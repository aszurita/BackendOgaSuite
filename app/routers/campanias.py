from fastapi import APIRouter, Depends, Query

from app.core.database import get_db
from app.core.permissions import get_current_user, require_oga_user
from app.models.auth import CurrentUser
from app.models.campanias import (
    CampaniaClasificacion, CampaniaClasificacionCreate,
    CampaniaSeguimientoResumen, CampaniaStats,
)
from app.services import campanias_service

router = APIRouter()


@router.get("/clasificaciones", response_model=list[CampaniaClasificacion])
async def listar_clasificaciones(db=Depends(get_db)):
    """Lista clasificaciones de campanas con conteos de activos y terminados."""
    return campanias_service.get_clasificaciones(db)


@router.post("/clasificaciones", response_model=CampaniaClasificacion, status_code=201)
async def crear_clasificacion(
    body: CampaniaClasificacionCreate,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Crea una nueva clasificacion de campana. Requiere permisos OGA."""
    return campanias_service.crear_clasificacion(db, body)


@router.get("/seguimiento", response_model=list[CampaniaSeguimientoResumen])
async def get_seguimiento(
    clasificacion_id: int | None = Query(None),
    estado: str | None = Query(None),
    db=Depends(get_db),
):
    """
    Retorna seguimiento de iniciativas agrupado por codigo.
    Detecta automaticamente iniciativas terminadas por estado='T' o fecha_fin pasada.
    """
    return campanias_service.get_seguimiento(db, clasificacion_id, estado)


@router.get("/estadisticas", response_model=CampaniaStats)
async def estadisticas(
    clasificacion_id: int | None = Query(None),
    db=Depends(get_db),
):
    """Retorna estadisticas globales de campanas."""
    return campanias_service.get_estadisticas(db, clasificacion_id)
