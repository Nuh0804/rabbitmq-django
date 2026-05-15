"""
settings_additions.py
----------------------
Add ONLY these settings to your existing settings.py.
Everything here is non-default — skip anything already in your settings.

Copy-paste each section into the relevant place in settings.py.
"""


# ── INSTALLED_APPS additions ──────────────────────────────────────────────────
# Add to your INSTALLED_APPS list:

INSTALLED_APPS_ADDITIONS = [
    "graphene_django",
    "gateway",           # your gateway app
]


# ── Graphene configuration ────────────────────────────────────────────────────

GRAPHENE = {
    "SCHEMA": "gateway.schema.schema",

    # Adds execution_time_ms to every response — useful for performance debugging
    "MIDDLEWARE": [
        "graphene_django.debug.DjangoDebugMiddleware",   # remove in production
    ],

    # Allow introspection in development, disable in production
    # (introspection lets anyone see your full schema)
    "ATOMIC_MUTATIONS": False,   # we handle transactions per-service, not at gateway
}


# ── Async support ─────────────────────────────────────────────────────────────
# Required for async resolvers (the gateway uses httpx with asyncio)
# Graphene-django supports async views from Django 4.1+

ASGI_APPLICATION = "your_project.asgi.application"   # replace your_project

# If you're using runserver (development), Django handles async automatically.
# In production use gunicorn with uvicorn worker:
#     gunicorn your_project.asgi:application -w 4 -k uvicorn.workers.UvicornWorker


# ── CORS (if your frontend is on a different origin) ──────────────────────────
# pip install django-cors-headers
# Add "corsheaders" to INSTALLED_APPS
# Add "corsheaders.middleware.CorsMiddleware" as FIRST item in MIDDLEWARE

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",    # React dev server
    "http://localhost:5173",    # Vite dev server
]
# In production replace with your actual frontend domain


# ── Logging — structured logs with correlation IDs ────────────────────────────

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "loggers": {
        "gateway": {
            "handlers": ["console"],
            "level": "DEBUG",       # change to INFO in production
            "propagate": False,
        },
        "httpx": {
            "handlers": ["console"],
            "level": "WARNING",     # httpx is chatty at DEBUG
        },
    },
}


# ── Environment variables needed in .env ─────────────────────────────────────
"""
Add these to your .env file (never commit .env):

# Service URLs — match your Docker Compose service names
ACCOUNT_SERVICE_URL=http://account_service:8006
ORDER_SERVICE_URL=http://order_service:8001
PAYMENT_SERVICE_URL=http://payment_service:8002
INVENTORY_SERVICE_URL=http://inventory_service:8003
SHIPPING_SERVICE_URL=http://shipping_service:8005
NOTIFICATION_SERVICE_URL=http://notification_service:8004

# Auth
JWT_SECRET=replace-with-a-long-random-string
JWT_ALGORITHM=HS256

# Gateway behaviour
SERVICE_TIMEOUT_SECONDS=10
DEBUG=True

# For local development you can use localhost with the service ports:
# ACCOUNT_SERVICE_URL=http://localhost:8006
# ORDER_SERVICE_URL=http://localhost:8001
# etc.
"""
