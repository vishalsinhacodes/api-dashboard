from pathlib import Path
import os
from dotenv import load_dotenv

# Determine repo root reliably (one level up from this file)
ROOT = Path(__file__).parent.parent.resolve()
DOTENV_PATH = ROOT / ".env"

# Load the .env file explicitly (if present)
if DOTENV_PATH.exists():
    load_dotenv(dotenv_path=str(DOTENV_PATH))
else:
    # fallback to default behavior (optional)
    load_dotenv()
    
API_PLAYGROUND = Path(os.getenv('API_PLAYGROUND_PATH', str(ROOT.parent))).resolve()
DATA_DIR = API_PLAYGROUND / 'data'
CHARTS_DIR = API_PLAYGROUND / 'charts'

RUN_TOKEN = os.getenv('DASHBOARD_RUN_TOKEN')
HOST = os.getenv('HOST', '127.0.0.1')
PORT = int(os.getenv('PORT', '8000'))
