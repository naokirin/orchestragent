"""Run the web dashboard: python -m orchestragent.dashboard.web"""

import os
import sys
from pathlib import Path

# Ensure project root and src are on path when run as __main__
_repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
_src = _repo_root / "src"
for p in (_repo_root, _src):
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

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
