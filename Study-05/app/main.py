"""AI 공감 다이어리 서버. 상태 없이 일기 본문을 분석만 한다(저장은 프론트 localStorage).

실행: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

API 계약
  POST /api/diary  {"text": str(공백 제거 후 1~2000자)}
    200: {primary_emotion, emotions[{name, intensity 1~5}], summary, empathy, comfort, crisis}
    실패: {"detail": "한국어 안내"}  400 요청 읽기 실패 / 403 호스트·출처 / 404·405 / 411·413 본문 / 422 입력
          / 429 혼잡·일일 한도·동시 요청 초과 / 500 서버 설정(키 없음) / 502 모델 실패(답변이 길어 잘린 경우 전용 문구) / 504 시간 초과
    일기에 위기 표현이 있으면 모델 호출 실패·서버 설정 오류·입력 오류 응답에 "crisis": true 가 추가된다.
    detail 은 본래 오류 문구만 담는다(109/112/119 안내 문구를 붙이지 않는다).
    위기 안내 문구는 서버가 아니라 화면이 책임진다: crisis:true 를 받으면 화면은 반드시 위기 안내 박스를 띄운다.
    위기 표현이 없으면 crisis 필드 자체가 없다.
    (본문을 읽기 전에 거절되는 403/411/413, 본문을 못 읽는 400/404/405, 본문을 모르는 예상 밖 500 은 제외)
    어떤 경로에서도 오류는 한국어 {"detail": ...} JSON + 보안 헤더로 나간다(평문 500 없음). detail 은 항상 한국어 문구다.
    200 성공 응답은 위기일 때 comfort 에 109/112/119 안내를 서버가 보장한다(모델이 안 썼을 때만 덧붙임).
    클라이언트가 연결을 끊으면 진행 중인 모델 호출을 취소한다(무료 한도 절약).
    응답 헤더 X-Model(실제 사용 모델), X-Elapsed-Ms 는 참고용.
  GET /api/health  {"ok": true, "key_configured": bool}
  주의: 응답 문자열은 모델이 만든 텍스트이므로 화면에서는 textContent로만 출력해야 한다(HTML 이스케이프 책임은 화면).
"""
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.openrouter import chat, extract_json_object, has_api_key, log, run_until_disconnect, run_with_fallback
from app.prompts import CALL_TIMEOUT, DEADLINE, MODELS, build_messages
from app.schemas import MAX_TEXT, DiaryIn, apply_crisis_safety, has_crisis_keyword, validate_analysis

HOST, PORT = "127.0.0.1", 8000
ALLOWED_HOSTS = {f"{HOST}:{PORT}", f"localhost:{PORT}"}
# 최악: 2000자가 전부 서로게이트 쌍(이모지 등)이라 \uXXXX\uXXXX(12바이트/글자)로 이스케이프되면 약 24KB + JSON 껍데기.
# 여유를 두고 32KB로 제한한다.
MAX_BODY = 32 * 1024
MAX_CONCURRENT = 3  # 동시에 처리하는 모델 호출 수(단일 사용자 로컬 전제)
KST = timezone(timedelta(hours=9))
STATIC = Path(__file__).parent / "static"
SECURITY_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    # 단일 index.html(인라인 CSS/JS)용 최소 정책. 외부 리소스는 전부 차단.
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; "
        "img-src 'self' data:; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}

app = FastAPI(title="AI 공감 다이어리", docs_url=None, redoc_url=None, openapi_url=None)


def _deny(status: int, msg: str) -> JSONResponse:
    return JSONResponse({"detail": msg}, status_code=status)


class LocalOnlyGuard:
    """로그인이 없으므로 Host(DNS rebinding)와 Origin(CSRF)을 검사하고, 본문 크기를 제한하며, 보안 헤더를 붙인다.
    순수 ASGI 미들웨어다. @app.middleware("http")(BaseHTTPMiddleware)는 본문을 읽은 뒤의 연결 끊김을
    핸들러에 전달하지 않아서 request.is_disconnected()가 동작하지 않는다(모델 호출 취소 불가)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).update(SECURITY_HEADERS)
            await send(message)

        headers = Headers(scope=scope)
        method = scope["method"]
        origin = headers.get("origin")
        length = headers.get("content-length", "")
        denied = None
        if headers.get("host", "") not in ALLOWED_HOSTS:
            denied = _deny(403, "허용되지 않는 주소입니다. http://127.0.0.1:8000 으로 접속하세요.")
        elif method not in ("GET", "HEAD") and origin and origin.removeprefix("http://") not in ALLOWED_HOSTS:
            denied = _deny(403, "허용되지 않는 출처입니다. http://127.0.0.1:8000 에서 열어 주세요.")
        elif method == "POST" and not length.isdigit():
            denied = _deny(411, "요청 형식이 올바르지 않습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.")
        elif method == "POST" and int(length) > MAX_BODY:
            denied = _deny(413, "보내는 내용이 너무 큽니다. 일기를 2000자 이내로 줄여 주세요.")
        if denied:
            await denied(scope, receive, send_with_headers)
        else:
            await self.app(scope, receive, send_with_headers)


app.add_middleware(LocalOnlyGuard)


def _error(status: int, msg: str, crisis: bool = False) -> JSONResponse:
    """오류 응답. 위기 표현이 있는 일기면 crisis=true만 붙인다(없으면 필드 자체를 넣지 않는다).
    위기 안내 문구(109 등)는 넣지 않는다: 그건 crisis:true를 보고 화면이 띄운다."""
    if crisis:
        return JSONResponse({"detail": msg, "crisis": True}, status_code=status)
    return _deny(status, msg)


def _crisis_in(body) -> bool:
    return isinstance(body, dict) and isinstance(body.get("text"), str) and has_crisis_keyword(body["text"])


@app.exception_handler(RequestValidationError)
async def on_validation_error(_request, exc):
    # pydantic 상세(입력 값 포함)는 노출하지 않고 쉬운 문구만 돌려준다.
    return _error(422, f"일기를 1자 이상 {MAX_TEXT}자 이하로 써 주세요.", _crisis_in(getattr(exc, "body", None)))


_HTTP_MESSAGES = {
    400: "요청을 읽지 못했어요. 페이지를 새로고침한 뒤 다시 시도해 주세요.",
    404: "찾을 수 없는 주소예요. http://127.0.0.1:8000 으로 접속하세요.",
    405: "허용되지 않는 요청 방식이에요.",
}
_HTTP_FALLBACK = "요청을 처리하지 못했어요. 잠시 후 다시 시도해 주세요."
_SERVER_ERROR = "서버에 문제가 생겼어요. 잠시 후 다시 시도해 주세요."


def _has_hangul(s: str) -> bool:
    return any("가" <= c <= "힣" for c in s)


@app.exception_handler(StarletteHTTPException)
async def on_http_error(_request, exc):
    # detail이 한글을 포함하면(우리가 직접 쓴 문구) 그대로, 아니면(Starlette/FastAPI 영어 기본 문구) 사전으로 대체한다.
    # 400은 항상 사전 문구(본문 파싱 실패 등 영어 문구가 다양함).
    detail = exc.detail
    if exc.status_code != 400 and isinstance(detail, str) and _has_hangul(detail):
        msg = detail
    else:
        msg = _HTTP_MESSAGES.get(exc.status_code, _SERVER_ERROR if exc.status_code >= 500 else _HTTP_FALLBACK)
    return JSONResponse({"detail": msg}, status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.exception_handler(Exception)
async def on_unexpected_error(_request, exc):
    """예상 못 한 예외의 최후 방어선. 이 핸들러는 보안 미들웨어보다 바깥(ServerErrorMiddleware)에서 실행되므로
    보안 헤더를 직접 붙인다. 본문을 모르니 crisis 필드는 없다. 예외 내용은 응답에 넣지 않는다(타입만 로그)."""
    log.error("unexpected %s", type(exc).__name__)
    return JSONResponse({"detail": _SERVER_ERROR}, status_code=500, headers=SECURITY_HEADERS)


def daily_limit_message(now: datetime | None = None) -> str:
    """무료 일일 한도는 UTC 00:00(= 한국 09:00)에 리셋된다. 한국 0~9시에는 '오늘', 그 외에는 '내일'."""
    kst = (now or datetime.now(timezone.utc)).astimezone(KST)
    day = "오늘" if kst.hour < 9 else "내일"
    return f"오늘 쓸 수 있는 무료 AI 사용량을 다 썼어요. {day} 오전 9시(한국 시간) 이후에 다시 시도해 주세요."


def failure(last) -> tuple[int, str]:
    if last == "daily":
        return 429, daily_limit_message()
    if last == 429:
        return 429, "지금 AI가 많이 바빠요. 잠시 후 다시 눌러 주세요."
    if last == "parse":
        return 502, "AI의 답변을 정리하지 못했어요. 한 번 더 시도해 주세요."
    if last == "network":
        return 504, "네트워크 연결이 불안정해요. 인터넷 연결을 확인하고 다시 시도해 주세요."
    if last == "length":
        return 502, "답변이 길어져 끝내지 못했어요. 다시 시도해 주세요."
    if last == "timeout":
        return 504, "답변이 너무 오래 걸려요. 잠시 후 다시 시도해 주세요."
    return 502, "AI와 연결하지 못했어요. 잠시 후 다시 시도해 주세요."


_active = 0  # 처리 중인 모델 호출 수(이벤트 루프 하나라 락 불필요)


@app.post("/api/diary")
async def api_diary(request: Request, body: DiaryIn):
    global _active
    text = body.text.strip()
    crisis = has_crisis_keyword(text)
    if not 1 <= len(text) <= MAX_TEXT:
        return _error(422, f"일기를 1자 이상 {MAX_TEXT}자 이하로 써 주세요.", crisis)
    if not has_api_key():
        return _error(500, "서버 설정이 아직 끝나지 않았어요. 서버 관리자(.env의 API 키)를 확인해 주세요.", crisis)
    if _active >= MAX_CONCURRENT:
        return _error(429, "지금 처리 중인 요청이 많아요. 잠시 후 다시 눌러 주세요.", crisis)
    messages = build_messages(text)
    started = time.perf_counter()
    _active += 1
    try:
        async with httpx.AsyncClient(timeout=CALL_TIMEOUT) as client:
            out = await run_until_disconnect(
                run_with_fallback(
                    MODELS,
                    lambda model, max_tokens: chat(client, model, messages, max_tokens),
                    lambda raw: validate_analysis(extract_json_object(raw)),
                    DEADLINE,
                ),
                request.is_disconnected,
            )
    except HTTPException:
        raise
    except Exception as e:  # 예상 못 한 실패도 위기 일기에는 crisis:true 오류 JSON으로 답한다(CancelledError는 BaseException이라 통과)
        log.error("diary unexpected %s len=%d", type(e).__name__, len(text), exc_info=True)
        return _error(502, "AI와 연결하지 못했어요. 잠시 후 다시 시도해 주세요.", crisis)
    finally:
        _active -= 1
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if out is None:  # 클라이언트가 연결을 끊음: 모델 호출은 이미 취소됐다. 응답을 읽을 사람이 없다.
        log.info("diary cancelled by client len=%d %dms", len(text), elapsed_ms)
        return Response(status_code=499)
    if "error" in out:
        log.warning("diary failed len=%d last=%s %dms", len(text), out["error"], elapsed_ms)
        status, msg = failure(out["error"])
        return _error(status, msg, crisis)
    usage = out["usage"]
    log.info("diary ok len=%d model=%s calls=%d tokens=%s/%s %dms", len(text), out["model"], out["calls"],
             usage.get("prompt_tokens"), usage.get("completion_tokens"), elapsed_ms)
    result = apply_crisis_safety(out["result"], text)
    return JSONResponse(result, headers={"X-Model": out["model"], "X-Elapsed-Ms": str(elapsed_ms)})


@app.get("/api/health")
async def health():
    return {"ok": True, "key_configured": has_api_key()}


@app.get("/")
async def index():
    page = STATIC / "index.html"
    if not page.is_file():
        raise HTTPException(404, "화면 파일(app/static/index.html)이 아직 없습니다.")
    return FileResponse(page)
