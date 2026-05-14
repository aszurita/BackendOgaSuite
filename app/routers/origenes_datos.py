from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.services import origenes_datos_service

router = APIRouter()


@router.get("", response_model=list[dict])
async def listar_origenes(db=Depends(get_db)):
    """Lista los servidores con sus conteos de bases, tablas y campos."""
    return origenes_datos_service.get_servidores(db)
