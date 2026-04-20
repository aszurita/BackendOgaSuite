from pydantic import BaseModel
from typing import Optional, Union


class Campo(BaseModel):
    """Representa un campo de la vista vw_metadatos_OGA."""

    campo:                          Optional[str]
    descripcion_campo:              Optional[str]
    id_atributo_relacionado:        Optional[int]
    nombre_atributo_relacionado:    Optional[str]
    descripcion_atributo_relacionado: Optional[str]
    largo_campo:                    Optional[str]
    sn_nulo_campo:                  Union[str, int]
    sn_golden_record_campo:         Optional[int]
