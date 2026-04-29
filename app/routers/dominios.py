from fastapi import APIRouter, Depends, Query

from app.core.database import get_db
from app.core.permissions import get_current_user, require_oga_user
from app.models.auth import CurrentUser
from app.models.dominios import (
    Dominio, DominioCreate, DominioUpdate, DominioStats, AvanceDominio, AvanceUpdate,
)
from app.models.common import OkResponse
from app.services import dominios_service

router = APIRouter()


@router.get("", response_model=list[Dominio])
async def listar_dominios(
    activos_only: bool = Query(True),
    db=Depends(get_db),
):
    """Lista todos los dominios. Por defecto solo los activos."""
    return dominios_service.get_dominios(db, activos_only)


@router.get("/{dominio_id}", response_model=Dominio)
async def get_dominio(dominio_id: int, db=Depends(get_db)):
    """Retorna un dominio por ID."""
    return dominios_service.get_dominio_by_id(db, dominio_id)


@router.get("/{dominio_id}/estadisticas", response_model=DominioStats)
async def estadisticas_dominio(dominio_id: int, db=Depends(get_db)):
    """Retorna estadisticas del dominio (casos, terminos, artefactos, tablas, estructura, avance)."""
    return await dominios_service.get_estadisticas(db, dominio_id)


@router.get("/{dominio_id}/tablas-oficiales")
async def tablas_oficiales(dominio_id: int, db=Depends(get_db)):
    """Retorna las tablas oficiales asociadas al dominio."""
    return dominios_service.get_tablas_oficiales(db, dominio_id)


@router.get("/{dominio_id}/terminos")
async def terminos_dominio(
    dominio_id: int,
    tipo: str | None = Query(None),
    db=Depends(get_db),
):
    """Retorna terminos y atributos del dominio. Filtrar por tipo: TERMINO, ATRIBUTO."""
    return dominios_service.get_terminos_por_dominio(db, dominio_id, tipo)


@router.get("/{dominio_id}/avances", response_model=list[AvanceDominio])
async def avances_dominio(dominio_id: int, db=Depends(get_db)):
    """Retorna el checklist de avances del dominio."""
    return dominios_service.get_avances(db, dominio_id)


@router.post("", response_model=Dominio, status_code=201)
async def crear_dominio(
    body: DominioCreate,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Crea un nuevo dominio. Requiere permisos OGA."""
    return dominios_service.crear_dominio(db, body)


@router.put("/{dominio_id}", response_model=Dominio)
async def actualizar_dominio(
    dominio_id: int,
    body: DominioUpdate,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Actualiza un dominio. Requiere permisos OGA."""
    return dominios_service.actualizar_dominio(db, dominio_id, body)


@router.put("/{dominio_id}/avances/{item_id}", response_model=AvanceDominio)
async def actualizar_avance(
    dominio_id: int,
    item_id: int,
    body: AvanceUpdate,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Marca o desmarca un item del checklist de avances. Requiere permisos OGA."""
    return dominios_service.actualizar_avance(db, dominio_id, item_id, body)
