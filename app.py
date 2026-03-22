import pyotp
import qrcode
import io
import os
from dotenv import load_dotenv
import base64
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()

app = FastAPI(title="TOTP Auth Sandbox")

app.add_middleware(SessionMiddleware, secret_key="super-secret-sandbox-key")

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "dummy-secret-if-missing")

@app.get("/")
async def root(request: Request):
    """Check if the user has a valid session."""
    if request.session.get("authenticated"):
        return {"status": "Access Granted", "message": "Welcome to the Hub!"}
    return {"status": "unauthorized", "action": "go to /login"}

@app.get("/setup")
async def setup():
    """Generates a QR code to scan with Google Authenticator."""
    uri = pyotp.totp.TOTP(ADMIN_SECRET).provisioning_uri(
        name="admin@homelab", 
        issuer_name="PortalAuth"
    )
    
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    base64_img = base64.b64encode(buf.getvalue()).decode("utf-8")
    
    html = f"""
    <html>
        <body style="text-align: center; margin-top: 50px; font-family: sans-serif;">
            <h1>1. Open Google Authenticator</h1>
            <h1>2. Scan this QR Code</h1>
            <img src="data:image/png;base64,{base64_img}">
            <br><br>
            <a href="/login" style="font-size: 20px;">Go to Login</a>
        </body>
    </html>
    """
    return HTMLResponse(html)

@app.get("/login")
async def login_get():
    """Show the login form."""
    html = """
    <html>
        <body style="text-align: center; margin-top: 50px; font-family: sans-serif;">
            <h2>Enter your 6-digit code</h2>
            <form method="post">
                <input name="token" type="text" autocomplete="off" autofocus 
                       style="font-size: 24px; text-align: center; width: 150px;" 
                       placeholder="000000" maxlength="6">
                <br><br>
                <button type="submit" style="font-size: 20px;">Login</button>
            </form>
        </body>
    </html>
    """
    return HTMLResponse(html)

@app.post("/login")
async def login_post(request: Request, token: str = Form(...)):
    """Verify the 6-digit code submitted by the user."""
    totp = pyotp.TOTP(ADMIN_SECRET)
    
    if totp.verify(token):
        request.session["authenticated"] = True
        return RedirectResponse(url="/", status_code=303)
    
    return HTMLResponse("<h1>Invalid Token. Go back and try again.</h1>", status_code=401)

@app.get("/logout")
async def logout(request: Request):
    """Destroy the session cookie."""
    request.session.clear()
    return RedirectResponse(url="/")