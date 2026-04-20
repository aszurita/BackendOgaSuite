"""
Configuración centralizada de la aplicación.
Todas las variables se cargan desde el archivo .env en la raíz del proyecto.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Carga el .env desde la raíz del proyecto (un nivel arriba de /app)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Variable de entorno '{name}' no encontrada. "
            f"Verifique que el archivo .env está configurado correctamente."
        )
    return value


# ─── Base de datos ────────────────────────────────────────────────────────────
DB_DRIVER: str = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
DB_SERVER: str = os.getenv("DB_SERVER", "GYEINTNEGDB01,4433")
DB_NAME:   str = os.getenv("DB_NAME",   "PROCESOS_BI")
DB_TIMEOUT: int = int(os.getenv("DB_TIMEOUT", "10"))

# ─── Claves de IA ─────────────────────────────────────────────────────────────
OPENAI_API_KEY:    str = _require("OPENAI_API_KEY")
GEMINI_API_KEY:    str = _require("GEMINI_API_KEY")
ANTHROPIC_API_KEY: str = _require("ANTHROPIC_API_KEY")

# ─── WhatsApp BuilderBot ──────────────────────────────────────────────────────
BUILDERBOT_URL:     str = os.getenv("BUILDERBOT_URL", "")
BUILDERBOT_API_KEY: str = os.getenv("BUILDERBOT_API_KEY", "")

# ─── Servidor ─────────────────────────────────────────────────────────────────
APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT: int = int(os.getenv("APP_PORT", "8510"))

# ─── Rutas sin timeout de BD (para endpoints que llaman a IA) ─────────────────
NO_TIMEOUT_PATHS: frozenset[str] = frozenset({
    "/mermaid-diagram",
    "/mermaid-diagram-Gemini",
    "/mermaid-diagram-Claude",
})

# ─── Umbral de logging para consultas lentas (segundos) ───────────────────────
SLOW_QUERY_THRESHOLD_SECONDS: float = 5.0
