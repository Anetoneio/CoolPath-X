# ASTRA COOLPATH X — scaffold

Satellite-assisted heat-aware workforce scheduling platform for Ahmedabad municipal outdoor
workers. Hackathon build (9 h). Contract-first: every API response matches /contracts.

## Run the engine (FastAPI)

```
cd engine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
# server -> http://localhost:8000
```

## Run the web dashboard

```
cd web
npm install          # react, vite, leaflet, react-leaflet, tailwindcss
npm run dev          # http://localhost:5173
```

API base URL is a single config constant in `web/src/config.js` defaulting to
`http://localhost:8000`.

## Folder ownership

- /data (raw + processed): A1
- /engine: A2
- /web: B1
- /contracts, /mocks, /docs: B2 (orchestrator)

## Contract-first rule

Never edit /contracts without explicit instruction. Every API response must match its
contract file before a task is marked done. No secrets or API keys in the repo.