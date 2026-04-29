from pydantic import BaseModel, Field
from datetime import datetime


class DominioBase(BaseModel):
    codigo_dominio: str | None = None
    descripcion_dominio: str | None = None
    tipo_base_datos: str | None = None
    descripcion_tipo: str | None = None
    responsable: str | None = None
    objetivo: str | None = None
    alcance: str | None = None
    estado: str | None = None


class DominioCreate(DominioBase):
    descripcion_dominio: str = Field(..., min_length=1, max_length=300)


class DominioUpdate(DominioBase):
    pass


class Dominio(DominioBase):
    id_dominio: int
    sn_activo: bool = True
    fecha_creacion: datetime | None = None
    fecha_modificacion: datetime | None = None

    model_config = {"from_attributes": True}


class DominioStats(BaseModel):
    cant_casos: int = 0
    cant_terminos: int = 0
    cant_atributos: int = 0
    cant_artefactos: int = 0
    cant_tablas: int = 0
    cant_estructura: int = 0
    porc_avance: float = 0.0


class AvanceDominio(BaseModel):
    id_avance: int
    descripcion: str | None = None
    completado: bool = False
    fecha_completado: datetime | None = None
    responsable: str | None = None


class AvanceUpdate(BaseModel):
    completado: bool


class SubdominioDominio(BaseModel):
    id_subdominio: int
    descripcion_subdominio: str | None = None
    responsable: str | None = None
    estado: str | None = None
