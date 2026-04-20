from pydantic import BaseModel, field_validator
from typing import Any, Dict, Optional


class SQLQuery(BaseModel):
    """
    Parámetros para construir un SELECT dinámico.
    El SQL resultante es: SELECT {campos} FROM {origen} WHERE {condicion}
    """
    campos:    str
    origen:    str
    condicion: str


class InsertQuery(BaseModel):
    """
    Parámetros para una operación INSERT.
    'datos' es un diccionario columna → valor.
    """
    tabla: str
    datos: Dict[str, Any]

    @field_validator("datos")
    @classmethod
    def datos_no_vacio(cls, v: dict) -> dict:
        if not v:
            raise ValueError("El diccionario 'datos' no puede estar vacío.")
        return v


class UpdateQuery(BaseModel):
    """
    Parámetros para una operación UPDATE.
    'datos' es un diccionario columna → nuevo_valor.
    'condicion' es el contenido de la cláusula WHERE.
    """
    tabla:    str
    datos:    Dict[str, Any]
    condicion: str

    @field_validator("datos")
    @classmethod
    def datos_no_vacio(cls, v: dict) -> dict:
        if not v:
            raise ValueError("El diccionario 'datos' no puede estar vacío.")
        return v

    @field_validator("condicion")
    @classmethod
    def condicion_no_vacia(cls, v: str) -> str:
        if not v.strip():
            raise ValueError(
                "La condición WHERE no puede estar vacía en un UPDATE "
                "(para evitar actualizar toda la tabla accidentalmente)."
            )
        return v


class ExecuteStoredProcedure(BaseModel):
    """
    Parámetros para ejecutar un Stored Procedure.
    'parameters' es opcional; si se proporciona, debe ser {nombre_param: valor}.
    """
    procedure_name: str
    parameters:     Optional[Dict[str, Any]] = {}
