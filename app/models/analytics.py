from pydantic import BaseModel
from datetime import datetime


class VisitaCreate(BaseModel):
    desc_pagina: str
    sub_pagina: str | None = None


class VisitaResumen(BaseModel):
    desc_pagina: str | None = None
    total_visitas: int = 0
    ultimo_acceso: datetime | None = None
