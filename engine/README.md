# Engine — COOLPATH X

Python 3.9+ (task specified 3.11; this environment provides 3.9.6, code is 3.9-compatible).
FastAPI + uvicorn. All endpoints serve mock responses from /mocks.

## Run

```bash
cd engine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py        # or: uvicorn main:app --reload
# server -> http://localhost:8000
```

## Test

```bash
pytest
```

CORS is enabled for http://localhost:5173 (web dev server).