from pydantic import BaseModel
from typing import Optional


class WhatsAppMessage(BaseModel):
    """
    Mensaje a enviar por WhatsApp a través de BuilderBot.

    - number:        Número destino con código de país. Ej: 593998022538
    - content:       Texto del mensaje.
    - mediaUrl:      (Opcional) URL o nombre de archivo de imagen adjunta.
    - checkIfExists: Si True, verifica que el número exista en WhatsApp.
    """
    number:        str
    content:       str
    mediaUrl:      Optional[str] = None
    checkIfExists: bool = False
