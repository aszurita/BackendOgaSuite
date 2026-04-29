from fastapi import APIRouter, Depends

from app.core.database import get_db, check_db_health
from app.core.permissions import get_current_user
from app.models.auth import CurrentUser, MeResponse
from app.models.common import HealthCheck
from app.services import auth_service

router = APIRouter()


@router.get("/me", response_model=MeResponse)
async def get_me(current_user: CurrentUser = Depends(get_current_user)):
    """Retorna perfil completo del usuario autenticado con permisos OGA por modulo."""
    return auth_service.get_me_response(current_user)


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """Verifica que el backend y la base de datos estan operativos."""
    db_ok = check_db_health()
    return HealthCheck(
        status="ok" if db_ok else "degraded",
        db_connected=db_ok,
        version="1.0.0",
    )
