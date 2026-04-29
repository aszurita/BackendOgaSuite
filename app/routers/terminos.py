from fastapi import APIRouter, Depends, Query

from app.core.database import get_db
from app.core.permissions import get_current_user, require_oga_user
from app.models.auth import CurrentUser
from app.models.terminos import (
    Termino, TerminoCreate, TerminoUpdate, TerminoResumen,
    SyncCasosUsoBody, DominioMapa, BuscarDuplicadoResponse,
)
from app.models.common import PaginatedResponse, OkResponse
from app.services import terminos_service

router = APIRouter()


@router.get("/terminos", response_model=PaginatedResponse[Termino])
async def listar_terminos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    buscar: str | None = Query(None),
    tipo: str | None = Query(None),
    dominio: str | None = Query(None),
    golden_record: bool | None = Query(None),
    dato_personal: int | None = Query(None),
    caracteristica: str | None = Query(None),
    db=Depends(get_db),
):
    """Lista terminos del glosario con filtros y paginacion server-side."""
    return terminos_service.get_terminos(
        db, page, page_size, buscar, tipo, dominio, golden_record, dato_personal, caracteristica
    )


@router.get("/terminos/recientes", response_model=list[Termino])
async def terminos_recientes(
    limit: int = Query(10, ge=1, le=50),
    db=Depends(get_db),
):
    """Retorna los N terminos modificados o creados mas recientemente."""
    return terminos_service.get_terminos_recientes(db, limit)


@router.get("/terminos/crosslinks", response_model=list[TerminoResumen])
async def crosslinks(db=Depends(get_db)):
    """Retorna id+nombre+tipo de todos los terminos activos para cross-linking."""
    return terminos_service.get_crosslinks(db)


@router.get("/terminos/buscar-duplicado", response_model=BuscarDuplicadoResponse)
async def buscar_duplicado(
    nombre: str = Query(...),
    tipo: str = Query(...),
    exclude_id: int | None = Query(None),
    db=Depends(get_db),
):
    """Verifica si ya existe un termino con el mismo nombre y tipo."""
    return terminos_service.buscar_duplicado(db, nombre, tipo, exclude_id)


@router.get("/terminos/{termino_id}", response_model=Termino)
async def get_termino(termino_id: int, db=Depends(get_db)):
    """Retorna un termino por ID."""
    return terminos_service.get_termino_by_id(db, termino_id)


@router.post("/terminos", response_model=Termino, status_code=201)
async def crear_termino(
    body: TerminoCreate,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Crea un nuevo termino en el glosario. Requiere permisos OGA."""
    return terminos_service.crear_termino(
        db, body, int(current_user.codigo_empleado) if current_user.codigo_empleado else None
    )


@router.put("/terminos/{termino_id}", response_model=Termino)
async def actualizar_termino(
    termino_id: int,
    body: TerminoUpdate,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Actualiza un termino existente. Requiere permisos OGA."""
    return terminos_service.actualizar_termino(
        db, termino_id, body,
        int(current_user.codigo_empleado) if current_user.codigo_empleado else None,
    )


@router.delete("/terminos/{termino_id}", response_model=OkResponse)
async def desactivar_termino(
    termino_id: int,
    motivo: str | None = Query(None),
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Desactiva (soft delete) un termino. Requiere permisos OGA."""
    terminos_service.desactivar_termino(
        db, termino_id, motivo,
        int(current_user.codigo_empleado) if current_user.codigo_empleado else None,
    )
    return OkResponse(message="Termino desactivado correctamente")


@router.get("/terminos/{termino_id}/casos-uso")
async def casos_uso_del_termino(termino_id: int, db=Depends(get_db)):
    """Retorna los casos de uso vinculados a un termino."""
    return terminos_service.get_casos_uso_del_termino(db, termino_id)


@router.put("/terminos/{termino_id}/casos-uso", response_model=OkResponse)
async def sync_casos_uso(
    termino_id: int,
    body: SyncCasosUsoBody,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Sincroniza las relaciones termino-caso_de_uso. Requiere permisos OGA."""
    terminos_service.sync_casos_uso(
        db, termino_id, body.casos_uso_ids,
        int(current_user.codigo_empleado) if current_user.codigo_empleado else None,
    )
    return OkResponse(message="Relaciones sincronizadas correctamente")


@router.get("/dominios-mapa", response_model=list[DominioMapa])
async def dominios_mapa(db=Depends(get_db)):
    """Retorna conteo de terminos activos por dominio para el sidebar."""
    return terminos_service.get_dominios_mapa(db)
