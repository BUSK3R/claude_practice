"""PRD 1단계: 냉장고 사진 재료 인식 서버.

실행: python -m app.main  (127.0.0.1:8000 에만 바인딩)
"""
import asyncio
import base64
import io
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError

from app.db import init_db
from app.openrouter import chat, extract_json_object, raise_for_failure, run_with_fallback
from app.recipes import router as recipes_router
from app.saved import router as saved_router

HOST = "127.0.0.1"
PORT = 8000
ALLOWED_HOSTS = {f"{HOST}:{PORT}", f"localhost:{PORT}"}

MODELS = [
    "nvidia/nemotron-3.5-super-vl:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
]
MAX_UPLOAD = 10 * 1024 * 1024
MAX_SIDE = 1280
MAX_PIXELS = 50_000_000  # 디코드 전 헤더 크기로 거부(압축 폭탄 방지). 8000x6250 정도까지 허용
MAX_TOKENS = 4000  # 추론 모델: 1500이면 3번 중 1번꼴로 content가 비어 옴
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

PROMPT = (
    "이 사진에 보이는 식재료만 찾아서 JSON으로만 답하세요. 설명이나 코드블록 없이 JSON 객체 하나만 출력합니다. "
    '형식: {"ingredients":[{"name":"한국어 재료명","quantity":"대략적인 수량","confidence":"high|medium|low"}]}. '
    "보이지 않는 재료는 추측해서 넣지 마세요. 식재료가 없으면 ingredients를 빈 배열로 두세요."
)


@asynccontextmanager
async def lifespan(_app):
    init_db()  # 스키마 초기화는 시작 시 1회
    yield


app = FastAPI(title="냉장고 재료 인식", lifespan=lifespan)
app.include_router(recipes_router)
app.include_router(saved_router)

SECURITY_HEADERS = {"X-Frame-Options": "DENY", "Content-Security-Policy": "frame-ancestors 'none'"}


@app.middleware("http")
async def local_only_guard(request, call_next):
    """로그인이 없으므로 다른 사이트가 브라우저를 통해 이 API를 호출하지 못하게 막는다
    (DNS rebinding: Host 검사, CSRF: 상태 변경 요청의 Origin 검사). 클릭재킹 방지 헤더도 붙인다."""
    if request.headers.get("host", "") not in ALLOWED_HOSTS:
        response = JSONResponse({"detail": "허용되지 않는 호스트입니다."}, status_code=403)
    else:
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD") and origin and origin.removeprefix("http://") not in ALLOWED_HOSTS:
            response = JSONResponse({"detail": "허용되지 않는 출처입니다."}, status_code=403)
        else:
            response = await call_next(request)
    response.headers.update(SECURITY_HEADERS)
    return response


def prepare_image(raw: bytes) -> str:
    """검증 후 긴 변 1280px 이하 JPEG로 재인코딩해 data URL 반환. 디스크에는 저장하지 않는다.
    CPU 작업이므로 호출 측에서 asyncio.to_thread로 실행한다."""
    try:
        img = Image.open(io.BytesIO(raw))
        if img.format not in ALLOWED_FORMATS:
            raise HTTPException(415, "JPEG, PNG, WebP 이미지만 올릴 수 있습니다.")
        if img.width * img.height > MAX_PIXELS:  # 헤더만 읽은 상태에서 거부
            raise HTTPException(413, "이미지 해상도가 너무 큽니다.")
        img.draft("RGB", (MAX_SIDE, MAX_SIDE))  # JPEG: 디코드 단계에서 축소해 시간·메모리 절약(그 외 포맷은 무시)
        img.load()
    except Image.DecompressionBombError:
        raise HTTPException(413, "이미지 해상도가 너무 큽니다.")
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise HTTPException(415, "이미지를 읽을 수 없습니다. 올바른 사진 파일인지 확인하세요.")
    img = ImageOps.exif_transpose(img)  # 휴대폰 사진의 회전 정보 반영
    img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def parse_ingredients(text: str) -> dict:
    items = extract_json_object(text)["ingredients"]
    if not isinstance(items, list):
        raise ValueError("ingredients가 목록이 아님")
    out = []
    for it in items[:30]:
        if not isinstance(it, dict):
            continue
        name = str(it["name"] if it.get("name") is not None else "").strip()[:40]
        if not name:
            continue
        quantity = str(it["quantity"] if it.get("quantity") is not None else "").strip()[:40]
        conf = str(it.get("confidence") or "medium").lower()
        out.append(
            {
                "name": name,
                "quantity": quantity,
                "confidence": conf if conf in ("high", "medium", "low") else "medium",
            }
        )
    return {"ingredients": out}


async def recognize(data_url: str) -> dict:
    messages = [{"role": "user", "content": [
        {"type": "text", "text": PROMPT},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]}]
    async with httpx.AsyncClient(timeout=90) as client:
        result = await run_with_fallback(
            MODELS,
            lambda model: chat(client, model, messages, MAX_TOKENS),
            parse_ingredients,
        )
    if "error" in result:
        raise_for_failure(result["error"], "재료를 직접 입력하세요.")
    return result


@app.post("/api/recognize")
async def api_recognize(file: UploadFile = File(...)):
    raw = await file.read(MAX_UPLOAD + 1)
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "파일이 너무 큽니다(최대 10MB).")
    return await recognize(await asyncio.to_thread(prepare_image, raw))


@app.get("/")
async def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
