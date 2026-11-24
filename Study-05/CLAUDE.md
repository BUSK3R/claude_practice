# CLAUDE.md

AI 공감 다이어리: 일기를 쓰면 AI가 감정을 분석하고 공감·위로 메시지를 돌려준다. FastAPI 로컬 서버가 `.env`의 키로 OpenRouter를 호출하고 `app/static/index.html`도 서빙한다. DB 없음(기록은 프론트 localStorage), 서버는 상태 없이 분석만 한다.

## 실행
- Python 3.11 이상 필요(`asyncio.timeout` 사용). 사람용 안내는 `README.md`.
- 설치: `pip install -r requirements.txt`
- 실행: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` (http://127.0.0.1:8000)
- `.env`에 `OPENROUTER_API_KEY` 필요(템플릿 `.env.example`). 값은 절대 출력·커밋하지 않는다.
- ad-hoc 스크립트에서 `app`을 import하려면 `PYTHONPATH=.` (`python -I`는 cwd를 뺀다).

## 구조
- `app/main.py`: 라우트(`POST /api/diary`, `GET /api/health`, `GET /`), Host/Origin/본문 크기(32KB) 순수 ASGI 미들웨어(보안 헤더·CSP 포함), 한국어 오류 문구, 동시 모델 호출 3개 제한. API 계약은 파일 상단 docstring.
  - 미들웨어는 `@app.middleware("http")`로 바꾸지 말 것: BaseHTTPMiddleware는 연결 끊김을 핸들러에 전달하지 않아 모델 호출 취소(`run_until_disconnect`)가 깨진다.
  - 일기에 위기 키워드가 있으면 모델 실패·설정 오류 응답에도 `"crisis": true`를 붙인다(`_error`). `detail`에는 109 문구를 넣지 않는다: 위기 안내 문구는 서버가 아니라 화면이 책임진다(`crisis:true`면 화면이 위기 박스를 반드시 띄움). 새 오류 경로를 추가하면 `_error`를 거치게 할 것.
  - 예상 못 한 예외는 `api_diary`의 `except Exception`(502+crisis)과 전역 `Exception` 핸들러(500, 본문 모름이라 crisis 없음)가 한국어 JSON으로 바꾼다. 전역 핸들러는 미들웨어 바깥에서 돌아 보안 헤더를 직접 붙인다. `detail`은 한글이 없으면(영어 기본 문구) 한국어 사전으로 대체, 400은 항상 사전 문구.
- `app/openrouter.py`: 호출, 백오프 재시도, 모델 폴백, 빈 응답/length 재요청, 연결 끊김 시 취소(`run_until_disconnect`), `extract_json_object`. 키는 여기서만 읽는다.
- `app/prompts.py`: 모델 ID, `MAX_TOKENS`, 타임아웃, 시스템 프롬프트(일기는 `<diary>` 구분자 안에 넣고 지시로 취급하지 않음).
- `app/schemas.py`: 요청 모델, 응답 스키마 검증, 위기 키워드 안전망(`CRISIS_KEYWORDS`, 109 안내 문구).

## 모델
기본 `nvidia/nemotron-3.5-lightning:free`, 폴백 `nvidia/nemotron-3-ultra-550b-a55b:free`. 둘 다 추론형이라 `max_tokens`가 작으면 content가 빈다. 현재 6000이고 length로 잘리면 재요청에 8000(상한)으로 올린다(4000은 실측에서 3800~3900에 잘렸다. 6000은 340자 일기 실측에서 5191토큰·호출 1회·28초로 통과, 8000은 실측 전). 모델당 최대 3회 호출(빈 응답·검증 실패·length는 1번만 재요청), 전체 150초 제한이며 호출별 타임아웃은 min(90초, 남은 시간), 남은 시간이 10초 미만이면 새 호출 없이 timeout.

## 보안 규칙
- 127.0.0.1 바인딩 유지. 로그인이 없으므로 Host/Origin 검사가 유일한 방어선이다.
- 로그에 일기 본문·키를 남기지 않는다(길이만). 오류 응답에 내부 정보 금지.
- 모델 출력은 신뢰하지 않고 서버에서 스키마 검증. 화면은 반드시 `textContent`로 출력.
- 위기 키워드가 있거나 모델이 `crisis:true`면 서버가 `comfort`에 109/112/119 안내를 보장한다.
- OpenRouter 무료 계정은 일일 한도(50회)가 있고 초과하면 429 `free-models-per-day`. 이때는 재시도 없이 즉시 안내한다.
