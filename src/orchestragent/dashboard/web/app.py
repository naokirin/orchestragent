"""
FastAPI application for the Web dashboard.
Serves read-only views of agent state (overview, tasks, intents, logs, settings).
Run independently of main.py; does not start the agent loop.
"""

import sys
from pathlib import Path

# Ensure project root is on path so "import config" works when run via uvicorn
# .../src/orchestragent/dashboard/web/app.py -> 5 levels up = repo root
_repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if _repo_root not in [Path(p).resolve() for p in sys.path]:
    sys.path.insert(0, str(_repo_root))

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from orchestragent.dashboard.web.routes import overview, settings as settings_route, tasks, logs, intents, plan  # noqa: E402
from orchestragent.dashboard.web.templates import render_dashboard  # noqa: E402

app = FastAPI(
    title="orchestragent Web Dashboard",
    description="Read-only dashboard for agent state (overview, tasks, intents, logs, settings).",
    version="0.1.0",
)

# Mount static assets if directory exists
_static_dir = Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the single-page dashboard (tabs: overview, logs, tasks, intents, settings)."""
    return HTMLResponse(render_dashboard())


# API routes
app.include_router(overview.router, prefix="/api", tags=["overview"])
app.include_router(settings_route.router, prefix="/api", tags=["settings"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
app.include_router(logs.router, prefix="/api", tags=["logs"])
app.include_router(intents.router, prefix="/api", tags=["intents"])
app.include_router(plan.router, prefix="/api", tags=["plan"])
