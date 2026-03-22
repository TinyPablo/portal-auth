# Overview: Portal Auth (TOTP + Traefik ForwardAuth)

## 1. System Persona & Output Rules
* **Zero Chatter:** You are a strict code generator senior software engineer. Output ONLY valid code, file contents, and necessary terminal commands. 
* **No Fluff:** Do NOT output conversational greetings, summaries, or phrases like "Here is the code" or "Let me know if you need help."
* **No Placeholders:** Write complete, functional code. Do NOT use comments like `# ... rest of code here` or `# implement logic`.
* **Structural Mandate:** Use `fastapi.templating.Jinja2Templates` and `fastapi.staticfiles.StaticFiles`. You MUST split the code:
    * `main.py`: Core logic and routes.
    * `templates/`: Jinja2 HTML files (`base.html`, `login.html`, `hub.html`, `setup.html`).
    * `static/`: CSS and assets.

## 2. Project Architecture
* **Purpose:** A lightweight Traefik ForwardAuth microservice acting as a gatekeeper for a homelab dashboard.
* **Authentication:** Single-user only. There is NO database and NO user registration. Authentication is strictly binary: the user must provide a 6-digit TOTP code that mathematically matches the `ADMIN_SECRET` environment variable.
* **State:** Upon successful TOTP validation, issue a secure, HTTP-only session cookie valid for 30 days.

## 3. Tech Stack
* **Backend:** Python 3.11+, FastAPI, Uvicorn, Jinja2.
* **Auth Libraries:** `pyotp` (TOTP validation), `qrcode[pil]` (QR rendering), `starlette.middleware.sessions`.
* **Frontend:** Pico CSS via CDN for a minimalist, classless dark-mode UI. Use a `base.html` to ensure a unified look across all pages.
* **Deployment:** Docker (Alpine or Slim base image).

## 4. Core Endpoints & Logic
The application MUST implement the following routes in `main.py`:

* `GET /auth-check`: The Traefik ForwardAuth gate. 
  * If the session cookie is valid, return `200 OK`. 
  * If invalid, return `401 Unauthorized` (Traefik will handle redirecting the unauthenticated user to the login portal). 
  * Must read the `X-Forwarded-Uri` header to understand what the user was trying to access.
* `GET /`: The main dashboard (Hub). Shows a simple grid of available homelab services. Protected by the session cookie.
* `GET /setup`: Renders the QR code for Google Authenticator based on the `.env` secret. Protected by the session cookie OR disabled in production via `DISABLE_SETUP=true`.
* `GET /login`: Renders the 6-digit PIN input form.
* `POST /login`: Validates the submitted PIN against `pyotp`. Sets the 30-day session cookie if successful and redirects to `/`.
* `GET /logout`: Destroys the session cookie and redirects to `/login`.

## 5. Deployment Constraints
* **Secrets:** NEVER hardcode secrets. Load `ADMIN_SECRET`, `SESSION_SECRET`, and `SECURE_COOKIES` via `os.getenv()`.
* **Docker:** Create a `Dockerfile` that:
  * Uses a minimal Python 3.11 image.
  * Installs dependencies from `requirements.txt` without caching.
  * Copies the `templates/` and `static/` folders into the image.
  * Runs the application as a non-root user for security.
  * Exposes port `5000`.
  * Starts the app using `gunicorn` with `uvicorn.workers.UvicornWorker`.