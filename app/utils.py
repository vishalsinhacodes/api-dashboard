from pathlib import Path
from datetime import datetime
from typing import List, Optional

def get_latest_mtime(paths: List[Path]) -> Optional[float]:
    """
    Return latest modification time (epoch seconds) among provided paths.
    Returns None if none of the files exist.
    """
    mtimes = []
    for p in paths:
        try:
            if p.exists():
                mtimes.append(p.stat().st_mtime)
        except Exception:
            continue
    return max(mtimes) if mtimes else None

def format_mtime_epoch(epoch: Optional[float]) -> Optional[str]:
    if not epoch:
        return None
    return datetime.fromtimestamp(epoch).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")