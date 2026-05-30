# Veritas AI

Autonomous multi-agent supply-chain compliance audits: three parallel agents (Bright Data + SERP) gather evidence; GPT-4o (via AIML API) synthesizes a truth score and verdict.

## Project layout

```
frontend/          Streamlit UI (Streamlit Cloud)
  app.py
  requirements.txt
backend/           FastAPI + agents (Railway)
  api/
  orchestration.py
  agents.py
main.py            Backend entrypoint
requirements-backend.txt
Dockerfile         Backend container
```

## Run the backend (local / Railway)

```powershell
cd "D:\veritas ai"
pip install -r requirements-backend.txt
python main.py
```

- **Swagger:** http://localhost:8000/docs  
- **Health:** `GET /health`  
- **Audits:** `POST /v1/audits/run`

**Docker:**

```powershell
docker build -t veritas-ai .
docker run -p 8000:8000 --env-file .env veritas-ai
```

## Run the frontend (local / Streamlit Cloud)

From repo root (works with Streamlit Cloud default `app.py`):

```powershell
cd "D:\veritas ai"
pip install -r requirements.txt
streamlit run app.py
```

Or run the frontend folder directly:

```powershell
cd "D:\veritas ai\frontend"
pip install -r requirements.txt
streamlit run app.py
```

**Streamlit Cloud**

| Setting | Value |
|---------|--------|
| Main file | `app.py` (root) or `frontend/app.py` |
| Requirements | `requirements.txt` (root includes frontend deps) |

Secrets (optional — no `.env` in the frontend):

```toml
VERITAS_API_URL = "https://veritas-ai-production-f85b.up.railway.app"
VERITAS_API_KEY = ""
SLACK_WEBHOOK_URL = ""
```

All agent work and API keys (`AIMLAPI`, Bright Data, etc.) stay on the **Railway backend** only.

- `AIMLAPI_API_KEY`, `BRIGHT_DATA_SBR_WS`, `BRIGHT_DATA_SERP_TOKEN`
- `VERITAS_API_KEY` (optional), `CORS_ORIGINS`, `PORT`

Do not commit `.env` or API keys.
