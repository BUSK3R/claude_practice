"""OpenRouter 호출: 재시도(지수 백오프), 모델 폴백, 빈 응답/길이 초과 재요청, JSON 추출.
API 키는 이 모듈의 api_key()에서만 읽는다(.env는 app/env.py가 로드). 키는 로그·응답에 남기지 않는다."""
import app.env  # noqa: F401  (.env 로드)

import asyncio
import json
import logging
import os
import re

import httpx

from app.prompts import CALL_TIMEOUT, MAX_TOKENS, MAX_TOKENS_CAP, MAX_TOKENS_STEP, MIN_CALL_SECONDS

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_ATTEMPTS_PER_MODEL = 3  # 모델당 총 호출 수(파싱 실패·빈 응답 재요청 포함)
MAX_SOFT_FAILURES = 2  # 빈 응답/길이 초과/검증 실패는 모델당 2번까지
MAX_RETRY_AFTER = 10  # Retry-After를 존중하되 이 이상 기다리지 않는다
log = logging.getLogger("uvicorn.error")


class UpstreamError(Exception):
    def __init__(self, status: int, message: str = "", retry_after: float | None = None, soft: bool = False):
        super().__init__(status, message)
        self.status, self.message, self.retry_after, self.soft = status, message, retry_after, soft


def has_api_key() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY"))


def _retry_after(r: httpx.Response) -> float | None:
    try:
        return max(0.0, min(float(r.headers.get("retry-after", "")), MAX_RETRY_AFTER))
    except ValueError:
        return None


async def chat(client: httpx.AsyncClient, model: str, messages: list, max_tokens: int) -> tuple[str, dict]:
    """모델 1회 호출. (content, usage) 반환. 빈 content나 finish_reason=length는 soft 실패."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise UpstreamError(401, "키 없음")
    body = {"model": model, "max_tokens": max_tokens, "messages": messages}
    r = await client.post(API_URL, json=body, headers={"Authorization": f"Bearer {key}"})
    if r.status_code == 429 and "free-models-per-day" in r.text:
        raise UpstreamError(429, "daily")  # 일일 무료 한도: 모델을 바꿔도 같은 한도라 재시도 무의미
    if r.status_code != 200:
        raise UpstreamError(r.status_code, retry_after=_retry_after(r))
    try:
        data = r.json()
        choice = data["choices"][0]
        content = choice["message"].get("content")
        finish = choice.get("finish_reason")
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        raise UpstreamError(502, "응답 형식 오류")
    if finish == "length":
        raise UpstreamError(200, "length", soft=True)  # 추론 토큰 포함 max_tokens 초과로 잘림
    if not content or not isinstance(content, str):
        raise UpstreamError(200, "빈 응답", soft=True)
    return content, usage


def extract_json_object(text: str) -> dict:
    """텍스트 안에서 첫 번째 유효한 JSON 객체(비어 있지 않은 dict)를 찾는다.
    '{'마다 raw_decode를 시도하므로 설명문 속 중괄호, 코드펜스, 뒤따르는 '}'에 영향받지 않는다.
    코드펜스는 지우지 않는다(문자열 값 안의 ```를 보존)."""
    dec = json.JSONDecoder()
    pos = text.find("{")
    if pos == -1:
        raise ValueError("JSON 없음")
    while pos != -1:
        try:
            obj, _ = dec.raw_decode(text, pos)
            if isinstance(obj, dict) and obj:
                return obj
        except ValueError:
            pass
        pos = text.find("{", pos + 1)
    raise ValueError("유효한 JSON 객체 없음")


async def run_with_fallback(models: list, attempt_fn, parse_fn, deadline: float):
    """모델마다 429/5xx/네트워크 오류는 백오프 재시도, 소진되면 다음 모델.
    attempt_fn(model, max_tokens) -> (text, usage), parse_fn(text) -> dict. 성공 시 dict에 model, usage, calls를 붙인다.
    실패 시 {"error": 마지막 원인("daily"|429|"parse"|"network"|"timeout"|"length"|...)}. 전체 소요는 deadline초로 제한한다.
    각 호출의 타임아웃은 min(CALL_TIMEOUT, 남은 시간)이라 첫 모델이 늦어도 폴백이 남은 시간 안에서 시도된다."""
    state = {"last": None, "calls": 0, "end": asyncio.get_running_loop().time() + deadline}
    try:
        async with asyncio.timeout(deadline):
            return await _run(models, attempt_fn, parse_fn, state)
    except TimeoutError:
        log.warning("deadline %ss exceeded (last=%s)", deadline, state["last"])
        return {"error": "timeout"}


async def run_until_disconnect(coro, is_disconnected, poll: float = 0.5):
    """coro를 태스크로 돌리면서 클라이언트 연결을 poll초마다 확인한다. 끊기면 태스크를 취소(재시도·폴백 중단)하고
    None을 돌려준다. 정상 종료하면 coro의 결과를 돌려준다. 바깥에서 취소돼도 안쪽 태스크를 남기지 않는다."""
    task = asyncio.ensure_future(coro)
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=poll)
            if done:
                return task.result()
            if await is_disconnected():
                return None
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)


async def _run(models, attempt_fn, parse_fn, state):
    for model in models:
        soft = 0
        length_hits = 0
        for attempt in range(MAX_ATTEMPTS_PER_MODEL):
            delay = 0.0
            remaining = state["end"] - asyncio.get_running_loop().time()
            if remaining < MIN_CALL_SECONDS:  # 남은 시간이 너무 적으면 새 호출을 시작하지 않는다
                log.warning("remaining %.1fs < %ss, not calling %s", remaining, MIN_CALL_SECONDS, model)
                state["last"] = "timeout"
                return {"error": "timeout"}
            state["calls"] += 1
            # length로 잘린 적이 있으면 이번에는 한도를 올려서 부른다(상한 MAX_TOKENS_CAP)
            tokens = min(MAX_TOKENS_CAP, MAX_TOKENS + MAX_TOKENS_STEP * length_hits)
            try:
                async with asyncio.timeout(min(CALL_TIMEOUT, remaining)):
                    text, usage = await attempt_fn(model, tokens)
                result = parse_fn(text)
                return {"result": result, "model": model, "usage": usage, "calls": state["calls"]}
            except UpstreamError as e:
                state["last"] = "length" if e.message == "length" else e.status
                if e.message == "length":
                    length_hits += 1
                log.warning("%s attempt %d -> upstream %s %s", model, attempt + 1, e.status, e.message)
                if e.message == "daily":
                    return {"error": "daily"}
                if e.soft:
                    soft += 1
                    if soft >= MAX_SOFT_FAILURES:
                        break
                elif e.status in (429, 502, 503, 504):
                    delay = e.retry_after if e.retry_after is not None else 2**attempt
                else:
                    break  # 401/402/404 등은 재시도해도 소용없으니 다음 모델로
            except TimeoutError:  # 이 호출의 시간 상한(asyncio.timeout)이 지남. 같은 모델을 또 기다리지 않고 다음 모델로
                state["last"] = "timeout"
                log.warning("%s attempt %d -> call timeout (%.0fs)", model, attempt + 1, min(CALL_TIMEOUT, remaining))
                break
            except httpx.TimeoutException:
                state["last"] = "network"
                log.warning("%s attempt %d -> network timeout", model, attempt + 1)
                delay = 2**attempt
            except httpx.DecodingError:  # 응답 압축 해제 실패 등: 재시도해도 같을 수 있어 백오프 없이 다음 시도
                state["last"] = "upstream"
                log.warning("%s attempt %d -> undecodable response", model, attempt + 1)
            except httpx.RequestError as e:  # TransportError·잘못된 요청 등 나머지 전부
                state["last"] = "network"
                log.warning("%s attempt %d -> network error (%s)", model, attempt + 1, type(e).__name__)
                delay = 2**attempt
            except (ValueError, KeyError, TypeError, IndexError, AttributeError) as e:
                state["last"] = "parse"
                log.warning("%s attempt %d -> parse/validation failed: %s", model, attempt + 1, e)
                soft += 1
                if soft >= MAX_SOFT_FAILURES:
                    break
            if delay and attempt < MAX_ATTEMPTS_PER_MODEL - 1:
                await asyncio.sleep(delay)
    return {"error": state["last"]}
