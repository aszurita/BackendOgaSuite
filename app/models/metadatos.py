from pydantic import BaseModel
from datetime import datetime


class TablaOficial(BaseModel):
    id: int
    plataforma: str | None = None
    servidor: str | None = None
    base: str | None = None
    esquema: str | None = None
    tabla: str | None = None
    descripcion_tabla: str | None = None
    data_owner: str | None = None
    nombre_data_owner: str | None = None
    data_steward: str | None = None
    nombre_data_steward: str | None = None
    id_clasificacion: int | None = None
    clasificacion: str | None = None
    etiquetas: str | None = None
    dominios: str | None = None
    fecha_modificacion_do: datetime | None = None
    fecha_modificacion_ds: datetime | None = None
    sn_activo: bool = True

    model_config = {"from_attributes": True}


class TablaUpdate(BaseModel):
    descripcion_tabla: str | None = None
    data_owner: str | None = None
    nombre_data_owner: str | None = None
    data_steward: str | None = None
    nombre_data_steward: str | None = None
    id_clasificacion: int | None = None
    etiquetas: str | None = None
    dominios: str | None = None


class Campo(BaseModel):
    llave_tabla: str | None = None
    campo: str | None = None
    tipo_dato: str | None = None
    longitud: int | None = None
    descripcion: str | None = None
    detalle: str | None = None
    plataforma: str | None = None
    servidor: str | None = None
    base: str | None = None
    esquema: str | None = None
    tabla: str | None = None
    id_fuente: int | None = None
    usuario_modificacion: str | None = None
    fecha_modificacion: datetime | None = None


class CampoUpdate(BaseModel):
    detalle: str | None = None
    descripcion: str | None = None


class RecomendacionDoc(BaseModel):
    campo: str
    sugerencia: str
    prefijo_detectado: str


class NodoEsquema(BaseModel):
    nombre: str
    tablas: list[str]


class NodoBase(BaseModel):
    nombre: str
    esquemas: list[NodoEsquema]


class NodoServidor(BaseModel):
    nombre: str
    bases: list[NodoBase]


class ArbolMetadatos(BaseModel):
    servidores: list[NodoServidor]
    cached_at: str


class Empleado(BaseModel):
    codigo: str
    nombre_completo: str


class FiltrosMetadatos(BaseModel):
    servidores: list[str]
    plataformas: list[str]
    clasificaciones: list[dict]
