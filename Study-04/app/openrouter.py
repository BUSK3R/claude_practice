"""OpenRouter 호출 공통 로직: 호출, 지수 백오프 재시도, 폴백 모델 전환, JSON 추출 헬퍼.
API 키는 .env(app/env.py가 로드)에서 이 모듈의 api_key()로만 읽는다."""
import app.env  # noqa: F401  (.env 로드)

import asyncio
import json
import logging
import os
import re

import httpx
from fastapi import HTTPException

API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_ATTEMPTS_PER_MODEL = 3  # 모델당 총 호출 수 상한(파싱 실패·빈 응답 재요청 포함)
MAX_SOFT_FAILURES = 2  # 파싱 실패/빈 응답/길이 초과는 모델당 2번까지(= 1번 재요청)
DEADLINE_SECONDS = 180  # run_with_fallback 전체 데드라인
MAX_RETRY_AFTER = 15  # Retry-After를 존중하되 이 이상은 기다리지 않는다
log = logging.getLogger("uvicorn.error")


class UpstreamError(Exception):
    def __init__(self, status: int, message: str = "", retry_after: float | None = None, soft: bool = False):
        super().__init__(status, message)
        self.status, self.message, self.retry_after = status, message, retry_after
        self.soft = soft  # 확률적 실패(빈 응답, 토큰 초과 등): 대기 없이 재요청


def api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise HTTPException(500, "서버에 OPENROUTER_API_KEY가 설정되지 않았습니다.")
    return key


def _retry_after(r: httpx.Response) -> float | None:
    try:
        return max(0.0, min(float(r.headers.get("retry-after", "")), MAX_RETRY_AFTER))
    except ValueError:
        return None


async def chat(client: httpx.AsyncClient, model: str, messages: list, max_tokens: int) -> str:
    body = {"model": model, "max_tokens": max_tokens, "messages": messages}
    r = await client.post(API_URL, json=body, headers={"Authorization": f"Bearer {api_key()}"})
    if r.status_code != 200:
        raise UpstreamError(r.status_code, retry_after=_retry_after(r))
    try:
        choice = r.json()["choices"][0]
        content = choice["message"].get("content")
        finish = choice.get("finish_reason")
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        raise UpstreamError(502, "응답 형식 오류")
    if finish == "length":  # 토큰 한도에서 잘림: JSON이 불완전하므로 파싱하지 않고 바로 재요청
        raise UpstreamError(200, "토큰 한도 초과(length)", soft=True)
    if not content or not isinstance(content, str):
        raise UpstreamError(200, "빈 응답", soft=True)  # 추론에 토큰을 다 쓴 경우
    return content


def extract_json_object(text: str) -> dict:
    """모델 응답에서 코드블록 표시를 걷어내고 첫 '{'부터 마지막 '}'까지를 JSON 객체로 파싱한다."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("JSON 없음")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("JSON 객체가 아님")
    return data


async def run_with_fallback(models: list, attempt_fn, parse_fn, deadline: float = DEADLINE_SECONDS):
    """각 모델마다 429/5xx/네트워크 오류를 백오프 재시도, 소진되면 다음 모델.
    attempt_fn(model)->str, parse_fn(str)->결과. 파싱 실패도 같은 시도 횟수에 포함된다.
    전체 소요 시간은 deadline초로 제한한다."""
    state = {"last": None}
    try:
        async with asyncio.timeout(deadline):
            return await _run(models, attempt_fn, parse_fn, state)
    except TimeoutError:
        log.warning("run_with_fallback deadline %ss exceeded (last=%s)", deadline, state["last"])
        return {"error": "timeout"}


async def _run(models, attempt_fn, parse_fn, state):
    for model in models:
        soft = 0
        for attempt in range(MAX_ATTEMPTS_PER_MODEL):
            is_last = attempt == MAX_ATTEMPTS_PER_MODEL - 1
            delay = 0.0
            try:
                return {**parse_fn(await attempt_fn(model)), "model": model}
            except UpstreamError as e:
                state["last"] = e.status
                log.warning("%s attempt %d -> upstream %s %s", model, attempt + 1, e.status, e.message)
                if e.soft:
                    soft += 1
                    if soft >= MAX_SOFT_FAILURES:
                        break
                elif e.status in (429, 502, 503, 504):
                    delay = e.retry_after if e.retry_after is not None else 2**attempt
                else:
                    break
            except (httpx.TimeoutException, httpx.TransportError):
                state["last"] = "network"
                log.warning("%s attempt %d -> network error", model, attempt + 1)
                delay = 2**attempt
            except (ValueError, KeyError, TypeError, IndexError, AttributeError):
                state["last"] = "parse"
                log.warning("%s attempt %d -> parse error", model, attempt + 1, exc_info=True)
                soft += 1
                if soft >= MAX_SOFT_FAILURES:
                    break
            if delay and not is_last:  # 마지막 시도 뒤에는 기다리지 않고 다음 모델로 넘어간다
                await asyncio.sleep(delay)
    return {"error": state["last"]}


def raise_for_failure(last, manual_hint: str):
    if last == 429:
        raise HTTPException(429, f"무료 모델이 혼잡합니다. 잠시 후 다시 시도하세요. {manual_hint}".strip())
    if last == "parse":
        raise HTTPException(502, f"모델 응답을 해석하지 못했습니다. {manual_hint}".strip())
    if last == "network":
        raise HTTPException(504, "네트워크 오류입니다. 연결을 확인하고 다시 시도하세요.")
    if last == "timeout":
        raise HTTPException(504, f"응답이 너무 오래 걸립니다. 잠시 후 다시 시도하세요. {manual_hint}".strip())
    raise HTTPException(502, f"요청에 실패했습니다. {manual_hint}".strip())
