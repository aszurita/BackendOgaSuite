from pydantic import BaseModel, Field
from datetime import datetime


class DominioBase(BaseModel):
    codigo_dominio: str | None = None
    cod_dominio: str | None = None
    descripcion_dominio: str | None = None
    nombre_dominio: str | None = None
    concepto_clave: str | None = None
    descripcion: str | None = None
    com: float | None = None
    impact: float | None = None
    tipo: str | None = None
    tipo_dominio: str | None = None
    familia: str | None = None
    lider_sugerido: str | None = None
    atributos_basicos: str | None = None
    id_tipo_dominio: int | None = None
    id_tipo_familia: int | None = None
    porcentaje_avance: float | None = None
    codificacion: str | None = None
    concepto: str | None = None


class DominioCreate(DominioBase):
    descripcion_dominio: str = Field(..., min_length=1, max_length=100)


class DominioUpdate(DominioBase):
    pass


class Dominio(DominioBase):
    id_dominio: int
    sn_activo: bool = True

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
