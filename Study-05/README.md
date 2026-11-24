# AI 공감 다이어리

일기를 쓰면 AI(OpenRouter 무료 모델)가 감정을 분석하고 공감·위로 메시지를 돌려주는 로컬 웹 앱입니다.
일기 기록은 서버가 아니라 브라우저(localStorage)에만 저장됩니다.

## 준비
- Python 3.11 이상 (`asyncio.timeout` 사용)
- [OpenRouter](https://openrouter.ai) API 키

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env      # 복사한 .env 안의 OPENROUTER_API_KEY 값을 본인 키로 바꾸기
```

## 실행 (Windows PowerShell, 이 폴더에서)
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
브라우저에서 http://127.0.0.1:8000 으로 접속합니다. (`localhost:8000`도 가능)
종료는 터미널에서 Ctrl+C.

- 포트·주소(127.0.0.1:8000)를 바꾸면 서버의 Host/Origin 검사에 막힙니다. 바꾸려면 `app/main.py`의 `HOST`, `PORT`도 같이 고쳐야 합니다.
- 이 폴더가 아닌 곳에서 실행하면 `app`을 찾지 못합니다. 스크립트에서 `app`을 import할 때는 `PYTHONPATH=.`이 필요합니다.

## index.html을 더블클릭하면 안 되는 이유
파일을 직접 열면 주소가 `file://...`가 되어 서버(`/api/diary`)에 요청을 보낼 수 없고, 서버도 허용되지 않은 출처로 거절합니다.
반드시 서버를 켠 뒤 위 주소로 접속하세요.

## 무료 한도
무료 모델은 계정당 하루 50회까지입니다. 초과하면 "오늘 쓸 수 있는 무료 AI 사용량을 다 썼어요" 안내가 나오고,
한도는 한국 시간 오전 9시(UTC 00:00)에 초기화됩니다. 한도가 소진된 뒤에는 재시도해도 소용없습니다.

## 안전 안내
일기에 위기 표현이 있으면 AI 호출이 실패해도 화면이 자살예방 상담전화 109(24시간), 긴급 시 112·119 안내 박스를 보여 줍니다(서버는 오류 응답에 `crisis: true`만 붙이고, 안내 문구는 화면이 책임집니다).
이 앱은 의료·상담 서비스가 아닙니다.
