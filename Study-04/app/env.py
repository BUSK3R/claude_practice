"""프로젝트 루트의 .env를 한 번 로드한다. 환경변수를 읽는 모듈(db, openrouter)이 가장 먼저 import 한다.
값을 출력하거나 다른 곳에 노출하지 않는다."""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
