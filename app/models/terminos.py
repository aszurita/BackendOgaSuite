from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

TipoTermino = Literal["TERMINO", "ATRIBUTO", "ATRIBUTO/TERMINO"]


class TerminoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=500)
    tipo: TipoTermino
    descripcion: str | None = None
    dominios: str | None = None               # Separados por ";"
    casos_uso: str | None = None              # Separados por ";"
    caracteristicas: str | None = None        # CDE, AR, etc.
    txt_desc_subcategoria: str | None = None
    dato_personal: int | None = None          # FK a categoria PDP (1-10)
    golden_record: bool = False
    catalogos_asociados: str | None = None
    etiqueta_tecnica: str | None = None
    prioridad: int | None = None


class TerminoCreate(TerminoBase):
    pass


class TerminoUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=500)
    tipo: TipoTermino | None = None
    descripcion: str | None = None
    dominios: str | None = None
    casos_uso: str | None = None
    caracteristicas: str | None = None
    txt_desc_subcategoria: str | None = None
    dato_personal: int | None = None
    golden_record: bool | None = None
    catalogos_asociados: str | None = None
    etiqueta_tecnica: str | None = None
    prioridad: int | None = None


class Termino(TerminoBase):
    id: int
    sn_activo: bool = True
    fecha_creacion: datetime | None = None
    fecha_modificacion: datetime | None = None
    autor_creacion: int | None = None
    autor_modificacion: int | None = None

    model_config = {"from_attributes": True}


class TerminoResumen(BaseModel):
    """Version reducida para crosslinks y mapas."""
    id: int
    nombre: str
    tipo: TipoTermino


class SyncCasosUsoBody(BaseModel):
    casos_uso_ids: list[int] = Field(default_factory=list)


class DominioMapa(BaseModel):
    dominio: str
    count: int


class BuscarDuplicadoResponse(BaseModel):
    es_duplicado: bool
    termino_existente_id: int | None = None
