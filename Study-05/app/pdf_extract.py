"""PDF 업로드 검증 + 텍스트 추출(메모리 처리 전용, 디스크 저장 없음).

라이브러리: PyMuPDF(pymupdf). 한글 PDF 추출 결과는 pypdf와 동일했고 속도가 20~200배 빨랐다(50쪽 0.02초 vs 4.3초).
주의: PyMuPDF는 스레드 안전하지 않아 전역 락으로 한 번에 하나만 추출한다. 라이선스는 AGPL-3.0이다
(로컬 개인 사용에는 문제없지만 배포·공개 서비스 시에는 확인 필요).

extract_pdf_text(data) 는 PdfError(status, code, 한국어 detail)만 던진다. 로그에는 문서 내용·파일명을 남기지 않는다.
"""
import asyncio
import re
import threading
import time
from dataclasses import dataclass

import pymupdf

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PAGES = 50
MIN_TEXT_CHARS = 50  # 공백 제외 글자가 이보다 적으면 스캔본/빈 PDF로 본다
MAX_USED_CHARS = 8_000
EXTRACT_TIMEOUT = 10.0  # 초
HEAD_SCAN = 1024

MESSAGES = {
    "bad_request": (400, "파일을 읽지 못했습니다. 다시 올려 주세요."),
    "not_pdf": (400, "PDF 파일이 아닙니다. PDF만 올릴 수 있어요."),
    "too_large": (413, "파일이 너무 큽니다. 10MB 이하 PDF를 올려 주세요."),
    "too_many_pages": (422, f"페이지가 너무 많습니다. {MAX_PAGES}쪽 이하 PDF를 올려 주세요."),
    "no_text": (422, "글자를 읽을 수 없는 PDF입니다. 스캔본이나 이미지 PDF는 지원하지 않아요."),
    "encrypted": (422, "암호가 걸린 PDF입니다. 암호를 푼 파일을 올려 주세요."),
    "corrupt": (422, "손상되었거나 열 수 없는 PDF입니다. 다른 파일로 시도해 주세요."),
    "timeout": (504, "시간이 너무 오래 걸려 중단했습니다. 더 짧은 문서로 시도해 주세요."),
}


class PdfError(Exception):
    def __init__(self, code: str):
        self.code = code
        self.status, self.detail = MESSAGES[code]
        super().__init__(code)


@dataclass
class Extracted:
    text: str  # 앞 MAX_USED_CHARS자까지(정리 후)
    page_count: int
    total_chars: int
    used_chars: int
    truncated: bool


_lock = threading.Lock()
pymupdf.TOOLS.mupdf_display_errors(False)  # MuPDF가 stderr에 내용 조각을 찍지 않게 한다

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACES = re.compile(r"[ \t 　]+")
_NEWLINES = re.compile(r"\n{3,}")


def clean_text(raw: str) -> str:
    t = _CTRL.sub("", raw.replace("\r\n", "\n").replace("\r", "\n"))
    t = _SPACES.sub(" ", t)
    t = re.sub(r" ?\n ?", "\n", t)
    return _NEWLINES.sub("\n\n", t).strip()


def _meaningful_len(text: str) -> int:
    return sum(1 for c in text if not c.isspace() and c != "�")


def _extract_sync(data: bytes, deadline: float) -> Extracted:
    repaired = False
    if not _lock.acquire(timeout=max(0.0, deadline - time.monotonic())):
        raise PdfError("timeout")
    try:
        try:
            doc = pymupdf.open(stream=data, filetype="pdf")
        except Exception:
            raise PdfError("corrupt") from None
        try:
            if doc.needs_pass:
                raise PdfError("encrypted")
            # 잘리거나 구조가 깨져 라이브러리가 억지로 복구한 파일. 다운로드가 끝에서 끊긴 정상 문서도 여기 걸리므로
            # 무조건 거절하지 않고, 복구 후에도 글자가 충분하면 통과시킨다(아래에서 글자가 모자라면 corrupt).
            repaired = bool(doc.is_repaired)
            try:
                pages = doc.page_count
            except Exception:
                raise PdfError("corrupt") from None
            if pages > MAX_PAGES:  # 글자 추출 전에 확인
                raise PdfError("too_many_pages")
            parts = []
            try:
                for i in range(pages):
                    if time.monotonic() > deadline:
                        raise PdfError("timeout")
                    parts.append(doc.load_page(i).get_text("text"))
            except PdfError:
                raise
            except Exception:
                raise PdfError("corrupt") from None
        finally:
            doc.close()
    finally:
        _lock.release()
    text = clean_text("\n".join(parts))
    if _meaningful_len(text) < MIN_TEXT_CHARS:
        raise PdfError("corrupt" if repaired else "no_text")  # 복구본에서 글자가 안 나오면 스캔본이 아니라 손상으로 본다
    used = text[:MAX_USED_CHARS]
    return Extracted(used, pages, len(text), len(used), len(text) > MAX_USED_CHARS)


async def extract_pdf_text(data: bytes) -> Extracted:
    """검증 + 추출. 이벤트 루프를 막지 않도록 스레드에서 실행하고 10초를 넘기면 포기한다."""
    if not data:
        raise PdfError("bad_request")
    if len(data) > MAX_PDF_BYTES:
        raise PdfError("too_large")
    if b"%PDF-" not in data[:HEAD_SCAN]:  # 확장자·Content-Type은 믿지 않는다
        raise PdfError("not_pdf")
    deadline = time.monotonic() + EXTRACT_TIMEOUT
    try:
        # 스레드는 쪽마다 deadline을 확인해 스스로 끝난다(스레드를 강제로 죽일 수는 없다).
        return await asyncio.wait_for(asyncio.to_thread(_extract_sync, data, deadline), EXTRACT_TIMEOUT + 1)
    except asyncio.TimeoutError:
        raise PdfError("timeout") from None
