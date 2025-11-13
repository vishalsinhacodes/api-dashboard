\# api-dashboard



FastAPI dashboard for automation reports.  

\*\*Depends on\*\* the sibling project `api-playground` which must generate the following files:



\- `api-playground/data/github\_repos\_latest.csv`

\- `api-playground/data/weather\_latest.csv`

\- `api-playground/data/crypto\_latest.csv`

\- `api-playground/charts/crypto\_latest.png`

\- `api-playground/charts/weather\_trend\_latest.png`



\## Quick start (local)



1. Copy `.env.example` → `.env` and set:
API_PLAYGROUND_PATH=D:\Vishal\dev\api-playground
DASHBOARD_RUN_TOKEN=<your-token>

2. Create venv, install:
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

3. Run:
.venv\Scripts\python -m uvicorn app.main:app --reload

4. Open `http://127.0.0.1:8000/`.

## Security
Do not expose the `/run` endpoint publicly. Keep `DASHBOARD_RUN_TOKEN` secret.


