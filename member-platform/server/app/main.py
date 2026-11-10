from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, org_errors
from .routes import accounts, auth, org_auth, org_content, org_meta, org_requests

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app):
    config.validate()
    db.init_db()
    yield


app = FastAPI(title="Alethic Insight 内部成员服务", version="0.1.0", lifespan=lifespan)
for router in (auth.router, accounts.router, accounts.admin_router, org_auth.router,
               org_content.router, org_meta.router, org_requests.router):
    app.include_router(router)
org_errors.install_org_error_handlers(app)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/health")
def health():
    return {"ok": True, "service": "member-platform", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse(config.PUBLIC_PREFIX + "/org")


def render_page(name):
    html = (STATIC_DIR / name).read_text(encoding="utf-8").replace("__PREFIX__", config.PUBLIC_PREFIX)
    html = html.replace('href="css/org.css"', f'href="{config.PUBLIC_PREFIX}/static/css/org.css"')
    for script in ("org.js", "login.js"):
        html = html.replace(f'src="{script}"', f'src="{config.PUBLIC_PREFIX}/static/{script}"')
    return HTMLResponse(html, headers={"Cache-Control": "no-store, must-revalidate"})


@app.get("/org", include_in_schema=False)
def org_page():
    return render_page("org.html")


@app.get("/login", include_in_schema=False)
def login_page():
    return render_page("login.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
