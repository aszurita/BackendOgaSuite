from fastapi import Depends, HTTPException, status

from app.core.auth import get_token_payload
from app.core.database import get_db
from app.models.auth import CurrentUser
from app.services import auth_service


async def get_current_user(
    token_payload: dict = Depends(get_token_payload),
    db=Depends(get_db),
) -> CurrentUser:
    """Dependency: retorna el usuario autenticado enriquecido con datos de BD."""
    return auth_service.enrich_user(db, token_payload)


async def require_oga_user(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Dependency: levanta HTTP 403 si el usuario no tiene rol OGA."""
    if not current_user.is_oga:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta operacion requiere permisos OGA",
        )
    return current_user
