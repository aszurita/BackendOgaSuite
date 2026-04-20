"""
Router: WhatsApp
Envío de mensajes de WhatsApp a través del servicio BuilderBot.

  POST /send-whatsapp
"""
import httpx
from fastapi import APIRouter, HTTPException

from app.config import BUILDERBOT_API_KEY, BUILDERBOT_URL
from app.schemas.whatsapp import WhatsAppMessage

router = APIRouter(prefix="", tags=["OGA Gestión"])

_WHATSAPP_TIMEOUT_SECONDS = 30.0


@router.post(
    "/send-whatsapp",
    summary="Enviar mensaje de WhatsApp",
    description=(
        "Envía un mensaje de texto (o con imagen adjunta) a través de BuilderBot. "
        "El número debe incluir código de país. Ej: `593998022538` para Ecuador."
    ),
)
async def send_whatsapp(message: WhatsAppMessage):
    headers = {
        "Content-Type": "application/json",
        "User-Agent":   "OGA-Backend/1.0",
        "x-api-key":    BUILDERBOT_API_KEY,
    }

    payload: dict = {
        "message": message.content,
        "number":  message.number,
    }
    if message.mediaUrl:
        payload["urlMedia"] = message.mediaUrl

    try:
        async with httpx.AsyncClient(verify=False, timeout=_WHATSAPP_TIMEOUT_SECONDS) as client:
            response = await client.post(
                BUILDERBOT_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

        return {
            "success":     True,
            "message":     "Mensaje enviado correctamente.",
            "number":      message.number,
            "status_code": response.status_code,
        }

    except httpx.HTTPStatusError as err:
        raise HTTPException(
            status_code=err.response.status_code,
            detail=(
                f"Error al enviar mensaje de WhatsApp: {err} "
                f"— Respuesta: {err.response.text}"
            ),
        )
    except httpx.RequestError as err:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo conectar con BuilderBot: {err}",
        )
    except Exception as err:
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado al enviar WhatsApp: {err}",
        )
