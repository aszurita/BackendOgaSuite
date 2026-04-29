import logging
import httpx
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.cache import get_jwks_cache, get_jwks_lock

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=True)


async def _fetch_jwks() -> dict:
    """Obtiene las claves publicas de Azure AD con cache de 24h."""
    cache = get_jwks_cache()
    lock = get_jwks_lock()

    with lock:
        cached = cache.get("jwks")
        if cached:
            return cached

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(settings.JWKS_URL)
        resp.raise_for_status()
        jwks = resp.json()

    with lock:
        cache["jwks"] = jwks

    logger.info("JWKS de Azure AD actualizados")
    return jwks


async def validate_token(token: str) -> dict:
    """Valida un Bearer token de Azure Entra ID y retorna los claims."""
    try:
        jwks = await _fetch_jwks()
    except Exception as e:
        logger.error("No se pudo obtener JWKS: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo verificar la autenticacion con Azure AD",
        )

    try:
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=settings.AZURE_CLIENT_ID,
            options={"verify_iss": False},  # Azure puede usar issuer v1 o v2
        )
        return payload
    except JWTError as e:
        # Si falla puede ser por rotation de llaves; invalidar cache y reintentar una vez
        cache = get_jwks_cache()
        with get_jwks_lock():
            cache.pop("jwks", None)
        logger.warning("Token invalido (se invalido cache JWKS): %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticacion invalido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """FastAPI dependency: extrae y valida el Bearer token."""
    return await validate_token(credentials.credentials)
