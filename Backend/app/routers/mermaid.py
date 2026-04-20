"""
Router: Mermaid Diagrams
Genera diagramas de flujo Mermaid a partir de código SQL/T-SQL
usando tres proveedores de IA distintos:

  POST /mermaid-diagram         → OpenAI GPT-4o
  POST /mermaid-diagram-Gemini  → Google Gemini Flash
  POST /mermaid-diagram-Claude  → Anthropic Claude Sonnet
"""
import re
from typing import Any

import anthropic
import google.generativeai as genai
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from openai import OpenAI

from app.config import ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY
from app.prompts.openai_prompt import MERMAID_PROMPT_OPENAI
from app.prompts.gemini_prompt import MERMAID_PROMPT_GEMINI

router = APIRouter(prefix="", tags=["OGA Gestión"])


# ─────────────────────────────────────────────────────────────────────────────
# Utilidad compartida: limpia y extrae el diagrama Mermaid del texto del modelo
# ─────────────────────────────────────────────────────────────────────────────
def _extract_mermaid(raw_text: str) -> str:
    """
    Normaliza el texto recibido de cualquier LLM y extrae únicamente
    el bloque de código Mermaid válido (flowchart / graph).
    """
    # 1. Normalizar fin de línea
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Convertir \\n a saltos reales si viene como texto escapado
    if "\\n" in text and ("flowchart" in text or "graph" in text):
        text = text.replace("\\n", "\n")

    # 3. Extraer bloque ```mermaid...``` si el modelo lo devolvió con fence
    if "```" in text:
        match = re.search(
            r"```(?:mermaid)?\s*(.*?)```",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if match:
            text = match.group(1).strip()

    # 4. Extraer solo líneas desde "flowchart" o "graph" en adelante
    lines = text.split("\n")
    mermaid_lines: list[str] = []
    collecting = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("flowchart", "graph")):
            collecting = True
        if collecting:
            # Cortar si empieza texto explicativo después del diagrama
            if stripped.startswith(("##", "Leyenda", "Explicación", "Nota", "Observación")):
                break
            mermaid_lines.append(line.rstrip())

    diagram = "\n".join(mermaid_lines).strip()

    # 5. Eliminar líneas vacías excesivas
    diagram = re.sub(r"\n{3,}", "\n\n", diagram).strip()

    # Si no se encontró un bloque válido, devolver el texto normalizado
    return diagram if diagram else text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# POST /mermaid-diagram — OpenAI GPT-4o
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/mermaid-diagram",
    response_class=PlainTextResponse,
    summary="Diagrama Mermaid (OpenAI GPT-4o)",
    description=(
        "Analiza el código SQL/T-SQL con GPT-4o y genera un diagrama "
        "de flujo Mermaid detallado con colores y subgrafos por fases."
    ),
)
async def mermaid_openai(sql_code: str) -> Any:
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": MERMAID_PROMPT_OPENAI},
            {"role": "user",   "content": f"Código SQL:\n\n{sql_code}"},
        ],
        temperature=0,
    )

    raw = (response.choices[0].message.content or "").strip()
    return _extract_mermaid(raw)


# ─────────────────────────────────────────────────────────────────────────────
# POST /mermaid-diagram-Gemini — Google Gemini Flash
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/mermaid-diagram-Gemini",
    response_class=PlainTextResponse,
    summary="Diagrama Mermaid (Google Gemini)",
    description=(
        "Analiza el código SQL/T-SQL con Google Gemini Flash y genera un diagrama "
        "Mermaid con subgrafos obligatorios y referencias explícitas a tablas."
    ),
)
async def mermaid_gemini(sql_code: str) -> Any:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(model_name="gemini-2.0-flash")

    prompt = f"{MERMAID_PROMPT_GEMINI}\n\nCódigo SQL:\n\n{sql_code}"

    result = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(temperature=0),
    )

    raw = (getattr(result, "text", None) or "").strip()
    return _extract_mermaid(raw)


# ─────────────────────────────────────────────────────────────────────────────
# POST /mermaid-diagram-Claude — Anthropic Claude Sonnet
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/mermaid-diagram-Claude",
    response_class=PlainTextResponse,
    summary="Diagrama Mermaid (Anthropic Claude)",
    description=(
        "Analiza el código SQL/T-SQL con Claude Sonnet y genera un diagrama "
        "Mermaid de alta calidad con fases, colores y checklist de validación."
    ),
)
async def mermaid_claude(sql_code: str) -> Any:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4000,
        temperature=0,
        system=MERMAID_PROMPT_OPENAI,
        messages=[
            {
                "role": "user",
                "content": f"Código SQL:\n\n{sql_code}",
            }
        ],
    )

    raw = ""
    if response.content:
        raw = response.content[0].text.strip()

    return _extract_mermaid(raw)
