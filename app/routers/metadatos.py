from fastapi import APIRouter, Depends, Query

from app.core.database import get_db
from app.core.permissions import get_current_user, require_oga_user
from app.core.cache import invalidar_arbol_cache
from app.models.auth import CurrentUser
from app.models.metadatos import (
    TablaOficial, TablaUpdate, Campo, CampoUpdate,
    ArbolMetadatos, RecomendacionDoc, Empleado, FiltrosMetadatos,
)
from app.models.common import PaginatedResponse, OkResponse
from app.services import metadatos_service, aprobaciones_service
from app.models.aprobaciones import AprobacionCreate

router = APIRouter()


@router.get("/filtros", response_model=FiltrosMetadatos)
async def get_filtros(db=Depends(get_db)):
    """Retorna listas de servidores, plataformas y clasificaciones para filtros UI."""
    return metadatos_service.get_filtros(db)


@router.get("/tablas", response_model=PaginatedResponse[TablaOficial])
async def listar_tablas(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    plataforma: str | None = Query(None),
    servidor: str | None = Query(None),
    base: str | None = Query(None),
    esquema: str | None = Query(None),
    clasificacion: str | None = Query(None),
    tabla: str | None = Query(None),
    owner_q: str | None = Query(None),
    owner_type: str | None = Query(None, description="'owner' o 'steward'"),
    db=Depends(get_db),
):
    """Lista tablas oficiales con filtros y paginacion server-side."""
    return metadatos_service.get_tablas(
        db, page, page_size, plataforma, servidor, base, esquema,
        clasificacion, tabla, owner_q, owner_type,
    )


@router.get("/tablas/{tabla_id}", response_model=TablaOficial)
async def get_tabla(tabla_id: int, db=Depends(get_db)):
    """Retorna detalle de una tabla por ID."""
    return metadatos_service.get_tabla_by_id(db, tabla_id)


@router.put("/tablas/{tabla_id}", response_model=TablaOficial)
async def update_tabla(
    tabla_id: int,
    body: TablaUpdate,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Actualiza metadatos de una tabla.
    - OGA: aplica el cambio directamente.
    - No-OGA: crea una solicitud de aprobacion PENDIENTE y retorna la tabla sin cambios.
    """
    if current_user.is_oga:
        return metadatos_service.update_tabla(
            db, tabla_id, body, current_user.email, current_user.codigo_empleado
        )
    else:
        aprobaciones_service.crear_desde_tabla_update(
            db, tabla_id, body, current_user.email,
            current_user.codigo_empleado or current_user.username,
        )
        return metadatos_service.get_tabla_by_id(db, tabla_id)


@router.get("/tablas/{tabla_id}/recomendaciones", response_model=list[RecomendacionDoc])
async def recomendaciones(tabla_id: int, db=Depends(get_db)):
    """Retorna sugerencias de documentacion para campos sin descripcion."""
    return metadatos_service.get_recomendaciones(db, tabla_id)


@router.get("/campos", response_model=PaginatedResponse[Campo])
async def listar_campos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    tabla_id: int | None = Query(None),
    buscar: str | None = Query(None),
    plataforma: str | None = Query(None),
    servidor: str | None = Query(None),
    base: str | None = Query(None),
    esquema: str | None = Query(None),
    tabla: str | None = Query(None),
    db=Depends(get_db),
):
    """Lista campos con busqueda multi-columna y filtros. Paginacion server-side."""
    return metadatos_service.get_campos(
        db, page, page_size, tabla_id, buscar, plataforma, servidor, base, esquema, tabla
    )


@router.put("/campos/{tabla_id}/{campo_nombre}", response_model=OkResponse)
async def update_campo(
    tabla_id: int,
    campo_nombre: str,
    body: CampoUpdate,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Actualiza definicion de un campo. Requiere permisos OGA."""
    result = metadatos_service.update_campo(
        db, tabla_id, campo_nombre, body,
        current_user.codigo_empleado or current_user.username,
    )
    return OkResponse(message=f"Campo '{campo_nombre}' actualizado")


@router.get("/arbol", response_model=ArbolMetadatos)
async def get_arbol(db=Depends(get_db)):
    """Retorna el arbol jerarquico servidor->base->esquema->tablas (con cache TTL 15min)."""
    return metadatos_service.get_arbol(db)


@router.delete("/arbol/cache", response_model=OkResponse)
async def invalidar_cache(
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Invalida el cache del arbol de metadatos. Requiere permisos OGA."""
    invalidar_arbol_cache()
    return OkResponse(message="Cache del arbol invalidado")


@router.get("/owners-facets", response_model=list[str])
async def owners_facets(
    tipo: str | None = Query(None, description="'owner' o 'steward'"),
    db=Depends(get_db),
):
    """Retorna lista de data owners o stewards unicos para autocompletado."""
    return metadatos_service.get_owners_facets(db, tipo)


@router.get("/empleados", response_model=list[Empleado])
async def get_empleados(db=Depends(get_db)):
    """Retorna lista de empleados activos para selector de data owner/steward."""
    return metadatos_service.get_empleados(db)
