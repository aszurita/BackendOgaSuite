import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger(__name__)


class OgaBaseException(Exception):
    def __init__(self, message: str, status_code: int = 500, code: str | None = None):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class NotFoundException(OgaBaseException):
    def __init__(self, message: str = "Recurso no encontrado"):
        super().__init__(message, status_code=404, code="NOT_FOUND")


class ForbiddenException(OgaBaseException):
    def __init__(self, message: str = "No tiene permisos para realizar esta operacion"):
        super().__init__(message, status_code=403, code="FORBIDDEN")


class UnauthorizedException(OgaBaseException):
    def __init__(self, message: str = "Autenticacion requerida"):
        super().__init__(message, status_code=401, code="UNAUTHORIZED")


class ConflictException(OgaBaseException):
    def __init__(self, message: str = "Conflicto con el estado actual del recurso"):
        super().__init__(message, status_code=409, code="CONFLICT")


class DatabaseException(OgaBaseException):
    def __init__(self, message: str = "Error de base de datos"):
        super().__init__(message, status_code=503, code="DB_ERROR")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(OgaBaseException)
    async def oga_exception_handler(request: Request, exc: OgaBaseException):
        if exc.status_code >= 500:
            logger.error("Error interno: %s | path=%s", exc.message, request.url.path)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = [
            {"campo": " -> ".join(str(loc) for loc in e["loc"]), "mensaje": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Error de validacion", "errors": errors, "code": "VALIDATION_ERROR"},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception("Error no manejado en %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Error interno del servidor", "code": "INTERNAL_ERROR"},
        )
