from fastapi import APIRouter, Depends, Query

from app.core.database import get_db
from app.core.permissions import get_current_user, require_oga_user
from app.models.auth import CurrentUser
from app.models.aprobaciones import (
    Aprobacion, AprobacionCreate,
    AprobacionAprobarBody, AprobacionRechazarBody,
)
from app.models.common import PaginatedResponse
from app.services import aprobaciones_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse[Aprobacion])
async def listar_aprobaciones(
    estado: str | None = Query(None, description="PENDIENTE | APROBADO | RECHAZADO | TODOS"),
    buscar: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db=Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Lista solicitudes de aprobacion con filtros y paginacion."""
    return aprobaciones_service.get_aprobaciones(db, estado, buscar, page, page_size)


@router.get("/{aprobacion_id}", response_model=Aprobacion)
async def get_aprobacion(
    aprobacion_id: int,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Retorna el detalle de una solicitud de aprobacion."""
    return aprobaciones_service.get_aprobacion_by_id(db, aprobacion_id)


@router.post("", response_model=Aprobacion, status_code=201)
async def crear_aprobacion(
    body: AprobacionCreate,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Crea una nueva solicitud de cambio en estado PENDIENTE."""
    return aprobaciones_service.crear_aprobacion(
        db, body, current_user.email, current_user.display_name
    )


@router.post("/{aprobacion_id}/aprobar", response_model=Aprobacion)
async def aprobar(
    aprobacion_id: int,
    body: AprobacionAprobarBody = AprobacionAprobarBody(),
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """
    Aprueba una solicitud y aplica el cambio correspondiente en la tabla afectada.
    Requiere permisos OGA.
    """
    return aprobaciones_service.aprobar_aprobacion(
        db, aprobacion_id, body,
        current_user.email,
        current_user.codigo_empleado or current_user.username,
    )


@router.post("/{aprobacion_id}/rechazar", response_model=Aprobacion)
async def rechazar(
    aprobacion_id: int,
    body: AprobacionRechazarBody,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Rechaza una solicitud y guarda el motivo. Requiere permisos OGA."""
    return aprobaciones_service.rechazar_aprobacion(
        db, aprobacion_id, body, current_user.email
    )
