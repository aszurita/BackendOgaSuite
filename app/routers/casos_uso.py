from fastapi import APIRouter, Depends, Query

from app.core.database import get_db
from app.core.permissions import get_current_user, require_oga_user
from app.models.auth import CurrentUser
from app.models.casos_uso import (
    CasoUso, CasoUsoCreate, CasoUsoUpdate,
    Fuente, FuenteCreate, Subdominio, ContadoresEstado,
)
from app.models.common import PaginatedResponse, OkResponse
from app.services import casos_uso_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse[CasoUso])
async def listar_casos_uso(
    id_dominio: int | None = Query(None),
    subdominio: str | None = Query(None),
    buscar: str | None = Query(None),
    estado: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    """Lista casos de uso con filtros y paginacion."""
    return casos_uso_service.get_casos_uso(db, id_dominio, subdominio, buscar, estado, page, page_size)


@router.get("/subdominios", response_model=list[Subdominio])
async def listar_subdominios(
    id_dominio: int | None = Query(None),
    db=Depends(get_db),
):
    """Lista subdominios activos, opcionalmente filtrados por dominio."""
    return casos_uso_service.get_subdominios(db, id_dominio)


@router.get("/contadores-estado", response_model=ContadoresEstado)
async def contadores_estado(
    id_dominio: int | None = Query(None),
    db=Depends(get_db),
):
    """Retorna conteos de casos de uso por estado (activos, terminados, total)."""
    return casos_uso_service.get_contadores_estado(db, id_dominio)


@router.get("/{caso_id}", response_model=CasoUso)
async def get_caso(caso_id: int, db=Depends(get_db)):
    """Retorna un caso de uso por ID."""
    return casos_uso_service.get_caso_by_id(db, caso_id)


@router.post("", response_model=CasoUso, status_code=201)
async def crear_caso_uso(
    body: CasoUsoCreate,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Crea un nuevo caso de uso. Requiere permisos OGA."""
    return casos_uso_service.crear_caso_uso(db, body)


@router.put("/{caso_id}", response_model=CasoUso)
async def actualizar_caso_uso(
    caso_id: int,
    body: CasoUsoUpdate,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Actualiza un caso de uso. Requiere permisos OGA."""
    return casos_uso_service.actualizar_caso_uso(db, caso_id, body)


@router.delete("/{caso_id}", response_model=OkResponse)
async def desactivar_caso_uso(
    caso_id: int,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Desactiva un caso de uso. Requiere permisos OGA."""
    casos_uso_service.desactivar_caso_uso(db, caso_id)
    return OkResponse(message="Caso de uso desactivado")


@router.get("/{caso_id}/fuentes", response_model=list[Fuente])
async def fuentes_caso_uso(caso_id: int, db=Depends(get_db)):
    """Retorna las fuentes de datos vinculadas a un caso de uso."""
    return casos_uso_service.get_fuentes_caso_uso(db, caso_id)


@router.post("/{caso_id}/fuentes", response_model=Fuente, status_code=201)
async def agregar_fuente(
    caso_id: int,
    body: FuenteCreate,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Agrega una fuente de datos a un caso de uso. Requiere permisos OGA."""
    return casos_uso_service.agregar_fuente(db, caso_id, body)


@router.delete("/{caso_id}/fuentes/{fuente_id}", response_model=OkResponse)
async def eliminar_fuente(
    caso_id: int,
    fuente_id: int,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Elimina una fuente de datos de un caso de uso. Requiere permisos OGA."""
    casos_uso_service.eliminar_fuente(db, caso_id, fuente_id)
    return OkResponse(message="Fuente eliminada")


@router.get("/{caso_id}/terminos")
async def terminos_caso_uso(caso_id: int, db=Depends(get_db)):
    """Retorna los terminos del glosario vinculados al caso de uso."""
    return casos_uso_service.get_terminos_caso_uso(db, caso_id)
