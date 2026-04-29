from pydantic import BaseModel, Field
from datetime import datetime


class CasoUsoBase(BaseModel):
    descripcion_caso_uso: str | None = None
    id_dominio: int | None = None
    subdominio: str | None = None
    objetivo: str | None = None
    estado: str | None = None
    responsable: str | None = None
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None


class CasoUsoCreate(CasoUsoBase):
    descripcion_caso_uso: str = Field(..., min_length=1, max_length=500)
    id_dominio: int


class CasoUsoUpdate(CasoUsoBase):
    pass


class CasoUso(CasoUsoBase):
    id_caso_uso: int
    sn_activo: bool = True
    fecha_creacion: datetime | None = None

    model_config = {"from_attributes": True}


class FuenteBase(BaseModel):
    id_fuente_aprovisionamiento: int | None = None
    txt_tabla: str | None = None
    descripcion: str | None = None
    tipo_fuente: str | None = None


class FuenteCreate(FuenteBase):
    id_fuente_aprovisionamiento: int
    txt_tabla: str = Field(..., min_length=1)


class Fuente(FuenteBase):
    id: int

    model_config = {"from_attributes": True}


class Subdominio(BaseModel):
    id_subdominio: int
    descripcion_subdominio: str | None = None
    id_dominio: int | None = None
    responsable: str | None = None
    estado: str | None = None
    sn_activo: bool = True


class ContadoresEstado(BaseModel):
    activos: int = 0
    terminados: int = 0
    total: int = 0
