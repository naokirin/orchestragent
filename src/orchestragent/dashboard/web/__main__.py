"""Run the web dashboard: python -m orchestragent.dashboard.web"""

import os
import sys
from pathlib import Path

# Ensure project root is on path so config loads (when run with PYTHONPATH=src)
_repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if _repo_root.exists() and str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("WEB_DASHBOARD_PORT", "8765"))
    host = os.getenv("WEB_DASHBOARD_HOST", "127.0.0.1")
    uvicorn.run(
        "orchestragent.dashboard.web.app:app",
        host=host,
        port=port,
        reload=os.getenv("WEB_DASHBOARD_RELOAD", "").lower() in ("1", "true"),
    )
