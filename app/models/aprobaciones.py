from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal

TipoCambio = Literal[1, 2, 3, 4, 5, 9]
EstadoAprobacion = Literal["PENDIENTE", "APROBADO", "RECHAZADO"]


class AprobacionCreate(BaseModel):
    tipo_cambio: TipoCambio
    tabla_id: int | None = None          # ID de la tabla afectada
    original: str | None = None          # Valor antes del cambio
    solicitado: str | None = None        # Valor nuevo solicitado
    dato1: str | None = None
    dato2: str | None = None
    dato3: str | None = None
    dato4: str | None = None
    dato5: str | None = None
    dato6: str | None = None
    dato7: str | None = None
    descripcion_cambio: str | None = Field(None, max_length=1000)


class AprobacionAprobarBody(BaseModel):
    comentario: str | None = None


class AprobacionRechazarBody(BaseModel):
    motivo: str = Field(..., min_length=1, max_length=500)


class Aprobacion(BaseModel):
    id: int
    tipo_cambio: int
    estado: EstadoAprobacion
    original: str | None = None
    solicitado: str | None = None
    autor_solicitud: str | None = None
    nombre_autor: str | None = None
    fecha_solicitud: datetime | None = None
    fecha_resolucion: datetime | None = None
    resolvio: str | None = None
    dato1: str | None = None
    dato2: str | None = None
    dato3: str | None = None
    dato4: str | None = None
    dato5: str | None = None
    dato6: str | None = None
    dato7: str | None = None
    dato8: str | None = None             # Motivo de rechazo
    descripcion_cambio: str | None = None

    model_config = {"from_attributes": True}
