from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_pool, close_pool
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging
from app.routers import auth, terminos, dominios, metadatos, aprobaciones, casos_uso, campanias, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_pool()
    yield
    close_pool()


app = FastAPI(
    title="OGA Suite API",
    description=(
        "Backend profesional para OGA Suite — Banco de Guayaquil. "
        "Gestiona el Glosario Empresarial, Explorador de Metadatos, "
        "Workflow de Aprobaciones, Dominios, Casos de Uso y Campanas."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

register_exception_handlers(app)

app.include_router(auth.router,         prefix="/auth",         tags=["Autenticacion"])
app.include_router(terminos.router,     prefix="/glosario",     tags=["Glosario"])
app.include_router(dominios.router,     prefix="/dominios",     tags=["Dominios"])
app.include_router(metadatos.router,    prefix="/metadatos",    tags=["Metadatos"])
app.include_router(aprobaciones.router, prefix="/aprobaciones", tags=["Aprobaciones"])
app.include_router(casos_uso.router,    prefix="/casos-uso",    tags=["Casos de Uso"])
app.include_router(campanias.router,    prefix="/campanias",    tags=["Campanas"])
app.include_router(analytics.router,    prefix="/analytics",    tags=["Analytics"])
