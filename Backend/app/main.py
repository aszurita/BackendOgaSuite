"""
OGA Gestión — Backend API
FastAPI application entry point.

Endpoints disponibles:
  GET  /campos                        → Metadata de columnas (vw_metadatos_OGA)
  POST /query                         → SELECT dinámico
  POST /insert                        → INSERT dinámico
  PUT  /update                        → UPDATE dinámico
  POST /execute-stored-procedure      → Stored Procedure
  POST /mermaid-diagram               → Diagrama Mermaid (OpenAI GPT-4o)
  POST /mermaid-diagram-Gemini        → Diagrama Mermaid (Google Gemini)
  POST /mermaid-diagram-Claude        → Diagrama Mermaid (Anthropic Claude)
  POST /send-whatsapp                 → Envío de mensaje WhatsApp

Documentación interactiva:
  GET  /docs    → Swagger UI personalizado
  GET  /scalar  → Scalar API Reference
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from scalar_fastapi import get_scalar_api_reference

from app.config import NO_TIMEOUT_PATHS
from app.database import DatabaseConnection
from app.routers import gestion, mermaid, whatsapp

# ─── Rutas de recursos estáticos ─────────────────────────────────────────────
_BASE_DIR = Path(__file__).resolve().parent.parent
_STATIC_DIR    = _BASE_DIR / "static"
_TEMPLATES_DIR = _BASE_DIR / "templates"


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan: inicialización y limpieza de recursos compartidos
# ─────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    db_conn = DatabaseConnection()
    app.state.db = db_conn
    app.state.no_timeout_paths = NO_TIMEOUT_PATHS
    yield
    # SHUTDOWN — SQLAlchemy libera el pool automáticamente al salir


# ─────────────────────────────────────────────────────────────────────────────
# Aplicación FastAPI
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    lifespan=lifespan,
    docs_url=None,    # desactivado: usamos Swagger personalizado en /docs
    redoc_url=None,
)

# ─── Archivos estáticos ───────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# ─── Templates ────────────────────────────────────────────────────────────────
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(gestion.router)
app.include_router(mermaid.router)
app.include_router(whatsapp.router)


# ─────────────────────────────────────────────────────────────────────────────
# OpenAPI personalizado con logo de Banco Guayaquil
# ─────────────────────────────────────────────────────────────────────────────
def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title="OGA Gestión",
        version="1.0.0",
        description=(
            "API de gestión de datos SQL Server para la suite OGA de Banco Guayaquil. "
            "Permite ejecutar consultas, inserciones, actualizaciones, stored procedures, "
            "generar diagramas Mermaid con IA y enviar mensajes por WhatsApp."
        ),
        routes=app.routes,
    )

    schema["info"]["x-logo"] = {"url": "/static/logo.png"}

    schema["tags"] = [
        {
            "name": "OGA Gestión",
            "description": (
                "Operaciones sobre SQL Server: metadata, SELECT, INSERT, UPDATE, "
                "stored procedures, diagramas Mermaid con IA y envío de WhatsApp."
            ),
        }
    ]

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = _custom_openapi


# ─────────────────────────────────────────────────────────────────────────────
# Swagger UI personalizado
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/docs", include_in_schema=False)
async def swagger_ui(request: Request):
    return templates.TemplateResponse(
        "custom_swagger.html",
        {
            "request":            request,
            "title":              "OGA Gestión",
            "openapi_url":        app.openapi_url,
            "swagger_js_url":     "https://cdn.jsdelivr.net/npm/swagger-ui-dist/swagger-ui-bundle.js",
            "swagger_css_url":    "https://cdn.jsdelivr.net/npm/swagger-ui-dist/swagger-ui.css",
            "swagger_favicon_url":"/static/logo.png",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Scalar API Reference
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/scalar", include_in_schema=False)
async def scalar_ui():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health", include_in_schema=False)
async def health():
    return JSONResponse({"status": "ok"})
