from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # MySQL
    SQL_HOST: str = "172.26.61.35"
    SQL_PORT: int = 3323
    SQL_DATABASE: str = "BG_OGASUITE"
    SQL_USER: str = "apl_ogasuite"
    SQL_PASSWORD: str = ""
    SQL_POOL_SIZE: int = 10
    SQL_POOL_TIMEOUT: int = 30
    SQL_CONNECT_TIMEOUT: int = 5
    SQL_CHARSET: str = "utf8mb4"

    # Azure Entra ID
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_JWKS_URL: str = ""

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:5175",
        "http://gobinfoana01-2:3000",
    ]

    # Cache TTLs (segundos)
    CACHE_TTL_ARBOL_SEGUNDOS: int = 900
    CACHE_TTL_TERMINOS_SEGUNDOS: int = 600
    CACHE_TTL_PERMISOS_SEGUNDOS: int = 300

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @property
    def JWKS_URL(self) -> str:
        if self.AZURE_JWKS_URL:
            return self.AZURE_JWKS_URL
        return (
            f"https://login.microsoftonline.com/"
            f"{self.AZURE_TENANT_ID}/discovery/v2.0/keys"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
