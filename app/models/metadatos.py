from pydantic import BaseModel, field_validator
from datetime import datetime


class TablaOficial(BaseModel):
    id: int
    id_fuente_aprovisionamiento: int | None = None
    txt_desc_tabla: str | None = None
    fuente: str | None = None
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

    @field_validator("data_owner", "data_steward", mode="before")
    @classmethod
    def coerce_to_str(cls, v):
        if v is None:
            return None
        return str(v)
    id_clasificacion: int | None = None
    clasificacion: str | None = None
    etiquetas: str | None = None
    dominios: str | None = None
    avance: float | None = None
    fecha_registro: datetime | None = None
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
    llave_unica: str | None = None
    campo: str | None = None
    # Campos con nombres originales que usa el frontend
    codigo: str | None = None           # id_atributos (vínculo al glosario)
    atributo: str | None = None         # descripción del atributo del glosario
    definicion: str | None = None       # detalle_campo (descripción del campo)
    tipo: str | None = None             # tipo de dato (legible)
    largo: str | None = None            # largo_atributo como string
    permite_null: str | None = None     # sn_nulo
    golden_record: str | None = None    # golden_record_campo
    ordinal_position: int | None = None
    # Campos de contexto de la tabla
    descripcion_tabla: str | None = None
    avance: str | None = None
    clasificacion: str | None = None
    nombre_data_owner: str | None = None
    nombre_data_steward: str | None = None
    # Campos técnicos de ubicación
    plataforma: str | None = None
    servidor: str | None = None
    base: str | None = None
    esquema: str | None = None
    tabla: str | None = None
    id_fuente: int | None = None
    id_fuente_aprovisionamiento: int | None = None
    # Campos de auditoría
    usuario_modificacion: str | None = None
    fecha_modificacion: datetime | None = None
    # Alias de compatibilidad (respuesta legacy del backend)
    tipo_dato: str | None = None
    longitud: int | None = None
    detalle: str | None = None
    descripcion: str | None = None


class CampoUpdate(BaseModel):
    detalle: str | None = None
    descripcion: str | None = None
    id_atributos: int | None = None     # None en JSON → limpia el atributo en BD


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
