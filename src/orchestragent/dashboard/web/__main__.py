"""Run the web dashboard: python -m orchestragent.dashboard.web"""

import os

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
