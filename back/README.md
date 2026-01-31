# Backend (FastAPI)

## Python 버전 (pyenv)
- 이 백엔드는 **pyenv 기준 Python 3.11.8**로 맞춰져 있어요.
- 파일:
  - `.python-version` → 로컬 pyenv 버전 핀
  - `runtime.txt` → Render 배포 시 파이썬 버전 지정

## Run locally (pyenv)
```bash
cd back
pyenv install 3.11.8
pyenv local 3.11.8

python -m venv .venv
.\.venv\Scripts\activate

pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

- Health: http://localhost:8000/health
- API: http://localhost:8000/api/v1/recommendations
