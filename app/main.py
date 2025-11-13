from datetime import datetime
import sys
import threading
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import subprocess
from pathlib import Path
import os
from app import config

app = FastAPI(title="Automation Dashboard")

# Templates & static
templates = Jinja2Templates(directory=str(Path(__file__).parent / 'templates'))
app.mount('/static', StaticFiles(directory=str(Path(__file__).parent / 'static')), name='static')

DATA = config.DATA_DIR
CHARTS = config.CHARTS_DIR
PLAYGROUND = config.API_PLAYGROUND

# Helper: safe file path
def safe_path(folder: Path, filename: str) -> Path:
    candidate = (folder / filename).resolve()
    if not str(candidate).startswith(str(folder.resolve())):
        raise HTTPException(status_code=400, detail='Invalid filename')
    return candidate

from fastapi.responses import JSONResponse
import pathlib, csv, os

@app.get("/_debug_data", response_class=JSONResponse)
async def debug_data():
    """
    Return quick diagnostics about the data and chart files the dashboard tries to load.
    This is read-only and safe to keep temporarily.
    """
    API_PLAYGROUND = config.API_PLAYGROUND
    DATA = config.DATA_DIR
    CHARTS = config.CHARTS_DIR

    def inspect_csv(path: pathlib.Path):
        if not path.exists():
            return {"exists": False}
        info = {"exists": True, "size": path.stat().st_size}
        try:
            with path.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = []
                cnt = 0
                for r in reader:
                    if cnt < 2:
                        rows.append(r)
                    cnt += 1
                info["rows"] = cnt
                info["sample"] = rows
        except Exception as e:
            info["error"] = str(e)
        return info

    def inspect_img(path: pathlib.Path):
        if not path.exists():
            return {"exists": False}
        return {"exists": True, "size": path.stat().st_size}

    out = {
        "api_playground_path": str(API_PLAYGROUND),
        "data_dir": str(DATA),
        "charts_dir": str(CHARTS),
        "github_repos_latest.csv": inspect_csv(DATA / "github_repos_latest.csv"),
        "weather_latest.csv": inspect_csv(DATA / "weather_latest.csv"),
        "crypto_latest.csv": inspect_csv(DATA / "crypto_latest.csv"),
        "crypto_chart": inspect_img(CHARTS / "crypto_latest.png"),
        "weather_chart": inspect_img(CHARTS / "weather_trend_latest.png"),
        # small env display (non-secret) to ensure env pointing correctly
        "env_API_PLAYGROUND_PATH": os.getenv("API_PLAYGROUND_PATH"),
        "env_dash_token_exists": bool(os.getenv("DASHBOARD_RUN_TOKEN")),
    }
    return out


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Proper home: load data files (latest snapshots), build the same context
    the template expects, render via TemplateResponse and return.
    Also prints a short preview for debugging if needed.
    """
    try:
        # Prepare paths
        DATA = config.DATA_DIR
        CHARTS = config.CHARTS_DIR
        CURR = os.getenv("CRYPTO_CURRENCY", "inr")

        # --- Read repos latest ---
        top_repos = []
        total_repos = 0
        total_stars = 0
        repos_file = DATA / "github_repos_latest.csv"
        print(repos_file)
        if repos_file.is_file():
            import csv
            rows = list(csv.DictReader(repos_file.open(newline="", encoding="utf-8")))
            # print(rows)
            for r in rows:
                r["stargazers_count"] = int(r.get("stargazers_count") or 0)
            rows.sort(key=lambda r: r["stargazers_count"], reverse=True)
            top_repos = rows[:5]
            total_repos = len(rows)
            total_stars = sum(r["stargazers_count"] for r in rows)

        totals = {"repos": total_repos, "stars": total_stars}

        # --- Read weather latest ---
        weather = {}
        weather_file = DATA / "weather_latest.csv"
        if weather_file.is_file():
            import csv
            weather = next(csv.DictReader(weather_file.open(newline="", encoding="utf-8")), {})

        # --- Read crypto latest ---
        crypto = {}
        crypto_file = DATA / "crypto_latest.csv"
        if crypto_file.is_file():
            prices = []
            latest_row = None
            import csv
            for row in csv.DictReader(crypto_file.open(newline="", encoding="utf-8")):
                # find price column (price_<curr>)
                price_key = next((k for k in row.keys() if k.startswith("price_")), None)
                if price_key:
                    try:
                        p = float(row.get(price_key) or 0.0)
                    except Exception:
                        p = 0.0
                    prices.append(p)
                    latest_row = row
            if prices:
                crypto = {
                    "latest_price": prices[-1],
                    "min_price": min(prices),
                    "max_price": max(prices),
                    "count": len(prices),
                    "latest_iso": latest_row.get("iso_time") if latest_row else None,
                }
                
        def _get_latest_mtime(paths):
            mtimes = []
            for p in paths:
                try:
                    if p.exists():
                        mtimes.append(p.stat().st_mtime)
                except Exception:
                    continue
            return max(mtimes) if mtimes else None
        
        # paths to check (data + charts)
        paths_to_check = [
            DATA / "github_repos_latest.csv",
            DATA / "weather_latest.csv",
            DATA / "crypto_latest.csv",
            CHARTS / "crypto_latest.png",
            CHARTS / "weather_trend_latest.png",
        ]
        latest_mtime = _get_latest_mtime(paths_to_check)
        if latest_mtime:
            last_updated = datetime.fromtimestamp(latest_mtime).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        else:
            last_updated = None

        # Build context expected by the template
        context = {
            "request": request,
            "top_repos": top_repos,
            "totals": totals,
            "weather": weather,
            "crypto": crypto,
            "ts": datetime.now().timestamp(),
            "last_updated": last_updated,
        }

        # Render via TemplateResponse (preferred) so Starlette handles headers correctly
        return templates.TemplateResponse("report.html", context)

    except Exception as exc:
        import traceback
        traceback.print_exc()
        return HTMLResponse(f"Server error while building template context: {exc}", status_code=500)
      
@app.get('/download/{filename}')
async def download(filename: str):
    # serve CSVs from data/
    p = safe_path(DATA, filename)
    if not p.exists():
        raise HTTPException(status_code=404, detail='Not Found')
    return FileResponse(str(p), media_type='text/csv', filename=p.name)

@app.get("/chart/{filename}")
async def chart(filename: str):
    """
    Serve chart images (PNG) from the charts directory.
    Example: /chart/crypto_latest.png
    """
    p = safe_path(config.CHARTS_DIR, filename)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(str(p), media_type="image/png", filename=p.name)

@app.post('/run')
async def run_pipeline(token: str = Form(...)):
    """Trigger the existing pipeline (runs run_daily_report.py)"""
    if not config.RUN_TOKEN or token != config.RUN_TOKEN:
        raise HTTPException(status_code=403, detail='Forbidden')
    
    PLAYGROUND = config.API_PLAYGROUND
    runner = PLAYGROUND / 'run_daily_report.py'
    if not runner.exists():
        raise HTTPException(status_code=404, detail='Runner not found in playground path')
    
    venv_py = PLAYGROUND / ".venv" / "Scripts" / "python.exe"
    python_exec = str(venv_py) if venv_py.exists() else sys.executable
    
    logs_dir = PLAYGROUND / "run_logs"
    logs_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    logpath = logs_dir / f"run_{ts}.log"    
    
    proc = subprocess.Popen(
        [python_exec, str(runner)],
        cwd=str(PLAYGROUND),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1
    )    
    
    def _stream_to_file(p, fpath):
        with open(fpath, "wb") as f:
            # read until process ends
            while True:
                chunk = p.stdout.read(1024)
                if not chunk:
                    break
                f.write(chunk)
                f.flush()
    t = threading.Thread(target=_stream_to_file, args=(proc, logpath), daemon=True)
    t.start()

    # 6) return immediate response with PID + log path
    return {"status": "started", "pid": proc.pid, "log": str(logpath)}

@app.get("/run/status")
async def run_status():
    logs_dir = config.API_PLAYGROUND / "run_logs"
    if not logs_dir.exists():
        return {"exists": False, "message": "no logs yet"}
    files = sorted(logs_dir.glob("run_*.log"))
    if not files:
        return {"exists": False, "message": "no logs yet"}
    latest = files[-1]
    return FileResponse(str(latest), media_type="text/plain", filename=latest.name)
