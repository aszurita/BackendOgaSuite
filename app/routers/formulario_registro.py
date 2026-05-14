from fastapi import APIRouter, Depends, HTTPException
from app.core.database import get_db
from app.core.permissions import require_oga_user
from app.models.auth import CurrentUser
from app.services import formulario_registro_service

router = APIRouter()


@router.get("/usuarios", response_model=list[dict])
async def listar_usuarios(db=Depends(get_db)):
    """Lista todos los usuarios Data Citizen registrados."""
    return formulario_registro_service.get_usuarios(db)


@router.put("/usuarios/{codigo}")
async def actualizar_usuario(codigo: str, payload: dict, db=Depends(get_db)):
    """Actualiza los datos de rol y habilidades de un usuario."""
    formulario_registro_service.update_usuario(db, codigo, payload)
    return {"ok": True}


@router.put("/usuarios/{codigo}/estado")
async def actualizar_estado_usuario(
    codigo: str,
    body: dict,
    db=Depends(get_db),
    current_user: CurrentUser = Depends(require_oga_user),
):
    """Actualiza el estado (ACTIVO/DESHABILITADO/PENDIENTE) de un usuario. Requiere permisos OGA."""
    estado = body.get("estado")
    if not estado:
        raise HTTPException(status_code=400, detail="Campo 'estado' requerido.")
    formulario_registro_service.update_usuario_estado(db, codigo, estado)
    return {"ok": True}
