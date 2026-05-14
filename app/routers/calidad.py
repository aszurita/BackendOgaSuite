from fastapi import APIRouter, Depends, Query
from app.core.database import get_db
from app.services import calidad_service

router = APIRouter()


@router.get("/calidad/ingenieros", response_model=list[dict])
async def listar_ingenieros(db=Depends(get_db)):
    """Lista los ingenieros de calidad disponibles."""
    return calidad_service.get_ingenieros_calidad(db)


@router.get("/calidad/backlog")
async def get_backlog(
    servidor: str = Query(...),
    base: str = Query(...),
    esquema: str = Query(...),
    tabla: str = Query(...),
    db=Depends(get_db),
):
    """Obtiene el ítem del backlog de calidad para una tabla específica."""
    return calidad_service.get_backlog_item(db, servidor, base, esquema, tabla)


@router.post("/calidad/backlog", status_code=201)
async def crear_backlog(body: dict, db=Depends(get_db)):
    """Crea un nuevo ítem en el backlog de calidad."""
    calidad_service.create_backlog_item(db, body)
    return {"ok": True}


@router.put("/calidad/backlog")
async def actualizar_backlog(body: dict, db=Depends(get_db)):
    """Actualiza el ingeniero asignado en el backlog de calidad."""
    calidad_service.update_backlog_item(db, body)
    return {"ok": True}


@router.get("/calidad/info")
async def get_calidad_info(
    clave: str = Query(...),
    db=Depends(get_db),
):
    """Retorna métricas de calidad para una tabla por su clave servidor.base.esquema.tabla."""
    parts = [p.strip().upper() for p in clave.split(".")]
    if len(parts) < 4:
        return None
    servidor, base, esquema, tabla = parts[0], parts[1], parts[2], parts[3]
    return calidad_service.get_calidad_info_by_clave(db, servidor, base, esquema, tabla)


@router.get("/empleados/{codigo}/web-user")
async def get_web_user(codigo: str, db=Depends(get_db)):
    """Obtiene el web_user de un empleado por su código."""
    web_user = calidad_service.get_web_user(db, codigo)
    return {"web_user": web_user}


@router.post("/mensajes/cola", status_code=201)
async def insertar_mensaje(body: dict, db=Depends(get_db)):
    """Inserta un mensaje en la cola de correos."""
    calidad_service.insert_cola_mensaje(db, body)
    return {"ok": True}
