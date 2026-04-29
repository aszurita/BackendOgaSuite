from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.core.permissions import get_current_user, require_oga_user
from app.models.auth import CurrentUser
from app.models.analytics import VisitaCreate, VisitaResumen
from app.models.common import OkResponse
from app.services import analytics_service

router = APIRouter()


@router.post("/visitas", response_model=OkResponse)
async def registrar_visita(
    body: VisitaCreate,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Registra una visita de pagina.
    Sustituye al hook useRegistrarVisita.js del frontend.
    Los errores se ignoran silenciosamente para no afectar la UX.
    """
    analytics_service.registrar_visita(db, body, current_user)
    return OkResponse(message="Visita registrada")


@router.get("/visitas/resumen", response_model=list[VisitaResumen])
async def resumen_visitas(
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Retorna resumen de visitas por pagina. Requiere permisos OGA."""
    return analytics_service.get_resumen_visitas(db)
