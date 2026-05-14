from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.services import catalogo_referencia_service

router = APIRouter()


@router.get("", response_model=list[dict])
async def listar_catalogo(db=Depends(get_db)):
    """Lista todos los registros del catálogo de referencia."""
    return catalogo_referencia_service.get_catalogo_referencia(db)


@router.get("/{codigo}/detalle", response_model=list[dict])
async def detalle_catalogo(codigo: str, db=Depends(get_db)):
    """Lista los ítems de detalle de un catálogo por su código."""
    return catalogo_referencia_service.get_catalogo_detalle(db, codigo)
