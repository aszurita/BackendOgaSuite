"""
Capa de acceso a la base de datos.

Clase DatabaseConnection:
  - Crea dos engines SQLAlchemy sobre SQL Server via pyodbc (Windows Auth).
  - Engine principal: con timeout configurado para requests normales.
  - Engine sin timeout: para endpoints de IA que pueden tardar más.
  - Expone get_session() para inyección de dependencias en FastAPI.
  - Expone query_metadata() para la vista vw_metadatos_OGA.
"""
import time
from datetime import datetime
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import (
    DB_DRIVER,
    DB_NAME,
    DB_SERVER,
    DB_TIMEOUT,
    SLOW_QUERY_THRESHOLD_SECONDS,
)
from app.schemas.campos import Campo

# ─────────────────────────────────────────────────────────────────────────────
# Log de consultas lentas
# ─────────────────────────────────────────────────────────────────────────────
_LOG_FILE = Path(__file__).resolve().parent.parent / "query_times.log"


def log_slow_query(duration: float, sql: str) -> None:
    """Registra en archivo las consultas que superan el umbral configurado."""
    if duration <= SLOW_QUERY_THRESHOLD_SECONDS:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} | {duration:.3f}s | {sql.strip()}\n"
    with open(_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


# ─────────────────────────────────────────────────────────────────────────────
# Clase de conexión
# ─────────────────────────────────────────────────────────────────────────────
class DatabaseConnection:
    """
    Pool de conexiones a SQL Server con autenticación Windows integrada.
    Se instancia una sola vez en el lifespan de la aplicación.
    """

    def __init__(self) -> None:
        connection_string = (
            f"mssql+pyodbc://@{DB_SERVER}/{DB_NAME}"
            f"?driver={DB_DRIVER}&TrustServerCertificate=yes"
        )

        # Engine con timeout (para la mayoría de endpoints)
        self._engine = create_engine(
            connection_string,
            connect_args={
                "timeout":       DB_TIMEOUT,
                "query_timeout": DB_TIMEOUT,
            },
            pool_pre_ping=True,     # verifica que la conexión esté viva
            pool_recycle=1800,      # recicla conexiones cada 30 min
        )

        # Engine sin timeout (para endpoints de IA: mermaid-diagram)
        self._engine_no_timeout = create_engine(
            connection_string,
            pool_pre_ping=True,
            pool_recycle=1800,
        )

        # Aplica timeout a nivel de cursor y LOCK_TIMEOUT en cada conexión
        self._register_timeout_events()

        self._SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self._engine
        )
        self._SessionNoTimeout = sessionmaker(
            autocommit=False, autoflush=False, bind=self._engine_no_timeout
        )

    def _register_timeout_events(self) -> None:
        """Registra eventos SQLAlchemy para aplicar timeouts a nivel driver."""

        def _set_cursor_timeout(conn, cursor, statement, parameters, context, executemany):
            try:
                cursor.timeout = DB_TIMEOUT
            except Exception:
                pass

        def _set_lock_timeout(dbapi_conn, connection_record):
            try:
                dbapi_conn.timeout = DB_TIMEOUT
                cursor = dbapi_conn.cursor()
                cursor.execute(f"SET LOCK_TIMEOUT {DB_TIMEOUT * 1000}")
                cursor.close()
            except Exception:
                pass

        event.listen(self._engine, "before_cursor_execute", _set_cursor_timeout)
        event.listen(self._engine, "connect", _set_lock_timeout)

    def get_session(self, no_timeout: bool = False) -> Session:
        """Devuelve una sesión SQLAlchemy. Usa engine sin timeout si se indica."""
        factory = self._SessionNoTimeout if no_timeout else self._SessionLocal
        return factory()

    def query_metadata(self, db: Session, params: dict) -> list[Campo]:
        """
        Consulta la vista de metadatos OGA para obtener información
        descriptiva de los campos de una tabla específica.
        """
        sql = """
            SELECT
                campo,
                descripcion_campo,
                id_atributo_relacionado,
                nombre_atributo_relacionado,
                descripcion_atributo_relacionado,
                largo_campo,
                sn_nulo_campo,
                sn_golden_record_campo
            FROM [PROCESOS_BI].[dbo].[vw_metadatos_OGA]
            WHERE servidor = :servidor
              AND base     = :base
              AND esquema  = :esquema
              AND tabla    = :tabla
        """
        start = time.time()
        result = db.execute(text(sql).execution_options(timeout=DB_TIMEOUT), params)
        rows = result.fetchall()
        log_slow_query(time.time() - start, sql)
        return [Campo(**row._mapping) for row in rows]
