from pydantic import BaseModel
from datetime import datetime


class CampaniaClasificacionBase(BaseModel):
    descripcion: str | None = None
    tipo: str | None = None
    estado: str | None = None


class CampaniaClasificacionCreate(CampaniaClasificacionBase):
    descripcion: str


class CampaniaClasificacion(CampaniaClasificacionBase):
    id: int
    num_activos: int = 0
    num_terminados: int = 0
    num_total: int = 0

    model_config = {"from_attributes": True}


class CampaniaSeguimientoResumen(BaseModel):
    codigo_iniciativa: str | None = None
    nombre: str | None = None
    estado: str | None = None
    num_activos: int = 0
    num_terminados: int = 0
    valor: int = 0
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    terminado: bool = False


class CampaniaStats(BaseModel):
    total_clasificaciones: int = 0
    total_iniciativas: int = 0
    total_activas: int = 0
    total_terminadas: int = 0
