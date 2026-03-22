import io
import os
import base64

import pyotp
import qrcode
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-me-in-production")
SECURE_COOKIES = os.getenv("SECURE_COOKIES", "true").lower() == "true"
DISABLE_SETUP = os.getenv("DISABLE_SETUP", "false").lower() == "true"
ALLOW_UNAUTHENTICATED_SETUP = os.getenv("ALLOW_UNAUTHENTICATED_SETUP", "false").lower() == "true"

COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

app = FastAPI(title="PortalAuth")

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    max_age=COOKIE_MAX_AGE,
    https_only=SECURE_COOKIES,
    same_site="lax",
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def is_authenticated(request: Request) -> bool:
    return request.session.get("authenticated") is True


@app.get("/auth-check")
async def auth_check(request: Request):
    forwarded_uri = request.headers.get("X-Forwarded-Uri", "/")
    if is_authenticated(request):
        return Response(status_code=200)
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": f'redirect="/login?next={forwarded_uri}"'},
    )


SERVICES = [
    {"name": "Traefik", "url": "https://traefik.local", "icon": "🔀"},
    {"name": "Portainer", "url": "https://portainer.local", "icon": "🐳"},
    {"name": "Grafana", "url": "https://grafana.local", "icon": "📊"},
    {"name": "Prometheus", "url": "https://prometheus.local", "icon": "🔥"},
    {"name": "Uptime Kuma", "url": "https://kuma.local", "icon": "🟢"},
    {"name": "Vaultwarden", "url": "https://vault.local", "icon": "🔐"},
    {"name": "Home Assistant", "url": "https://ha.local", "icon": "🏠"},
    {"name": "Nextcloud", "url": "https://cloud.local", "icon": "☁️"},
]


@app.get("/")
async def hub(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        "hub.html",
        {"request": request, "services": SERVICES},
    )


@app.get("/setup")
async def setup(request: Request):
    if DISABLE_SETUP:
        return Response(status_code=404)
    
    if not ALLOW_UNAUTHENTICATED_SETUP and not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)

    uri = pyotp.TOTP(ADMIN_SECRET).provisioning_uri(
        name="admin@homelab",
        issuer_name="PortalAuth",
    )

    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return templates.TemplateResponse(
        "setup.html",
        {"request": request, "qr_b64": qr_b64},
    )


@app.get("/login")
async def login_get(request: Request, error: int = 0, next: str = "/"):
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": bool(error), "next": next},
    )


@app.post("/login")
async def login_post(
    request: Request,
    token: str = Form(...),
    next: str = Form(default="/"),
):
    totp = pyotp.TOTP(ADMIN_SECRET)
    if totp.verify(token, valid_window=1):
        request.session["authenticated"] = True
        redirect_to = next if next.startswith("/") else "/"
        return RedirectResponse(url=redirect_to, status_code=303)
    return RedirectResponse(url=f"/login?error=1&next={next}", status_code=303)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)