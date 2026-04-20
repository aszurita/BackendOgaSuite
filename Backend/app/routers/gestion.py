"""
Router: OGA Gestión
Endpoints para operaciones sobre la base de datos SQL Server:
  POST /query                       → SELECT dinámico
  POST /insert                      → INSERT dinámico
  PUT  /update                      → UPDATE dinámico
  POST /execute-stored-procedure    → Ejecutar stored procedure
"""
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import DB_TIMEOUT
from app.database import DatabaseConnection, log_slow_query
from app.schemas.query import (
    ExecuteStoredProcedure,
    InsertQuery,
    SQLQuery,
    UpdateQuery,
)

router = APIRouter(prefix="", tags=["OGA Gestión"])


# ─────────────────────────────────────────────────────────────────────────────
# Dependencia de sesión (inyectada por FastAPI)
# ─────────────────────────────────────────────────────────────────────────────
def get_db(request: Request) -> Session:
    db_conn: DatabaseConnection = request.app.state.db
    no_timeout = request.url.path in request.app.state.no_timeout_paths
    session = db_conn.get_session(no_timeout=no_timeout)
    try:
        yield session
    finally:
        session.close()


# ─────────────────────────────────────────────────────────────────────────────
# Helper: detectar si un error es de timeout
# ─────────────────────────────────────────────────────────────────────────────
def _is_timeout(err: Exception) -> bool:
    msg = str(err).lower()
    return "timeout" in msg or "timed out" in msg


# ─────────────────────────────────────────────────────────────────────────────
# POST /query — SELECT dinámico
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/query",
    summary="Ejecutar SELECT",
    description=(
        "Construye y ejecuta: `SELECT {campos} FROM {origen} WHERE {condicion}`. "
        "Solo se permiten consultas SELECT."
    ),
)
async def select_records(query: SQLQuery, db: Session = Depends(get_db)):
    sql = f"SELECT {query.campos} FROM {query.origen} WHERE {query.condicion}"

    if not sql.strip().lower().startswith("select"):
        raise HTTPException(status_code=400, detail="Solo se permiten consultas SELECT.")

    start = time.time()
    try:
        result = db.execute(text(sql).execution_options(timeout=DB_TIMEOUT))
        columns = result.keys()
        rows = result.fetchall()
        log_slow_query(time.time() - start, sql)
        return [dict(zip(columns, row)) for row in rows]

    except Exception as err:
        if _is_timeout(err):
            log_slow_query(time.time() - start, f"{sql}  [TIMEOUT]")
            raise HTTPException(status_code=408, detail="Timeout al ejecutar la consulta.")
        raise HTTPException(status_code=400, detail=str(err))


# ─────────────────────────────────────────────────────────────────────────────
# POST /insert — INSERT dinámico
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/insert",
    summary="Insertar registro",
    description=(
        "Inserta un registro en la tabla indicada. "
        "'datos' es un diccionario {columna: valor}. "
        "Usa parámetros nombrados para prevenir SQL injection."
    ),
)
async def insert_record(query: InsertQuery, db: Session = Depends(get_db)):
    campos      = ", ".join(query.datos.keys())
    placeholders = ", ".join(f":{k}" for k in query.datos.keys())
    sql = f"INSERT INTO {query.tabla} ({campos}) VALUES ({placeholders})"

    start = time.time()
    try:
        result = db.execute(
            text(sql).execution_options(timeout=DB_TIMEOUT),
            query.datos,
        )
        db.commit()
        log_slow_query(time.time() - start, sql)
        return {
            "message":       f"Registro insertado correctamente en '{query.tabla}'.",
            "affected_rows": result.rowcount,
        }

    except Exception as err:
        db.rollback()
        if _is_timeout(err):
            log_slow_query(time.time() - start, f"{sql}  [TIMEOUT]")
            raise HTTPException(status_code=408, detail="Timeout al ejecutar el INSERT.")
        raise HTTPException(status_code=400, detail=str(err))


# ─────────────────────────────────────────────────────────────────────────────
# PUT /update — UPDATE dinámico
# ─────────────────────────────────────────────────────────────────────────────
@router.put(
    "/update",
    summary="Actualizar registros",
    description=(
        "Actualiza registros en la tabla indicada. "
        "'datos' es un diccionario {columna: nuevo_valor}. "
        "'condicion' es la cláusula WHERE (requerida para evitar actualizaciones masivas)."
    ),
)
async def update_record(query: UpdateQuery, db: Session = Depends(get_db)):
    set_clause = ", ".join(f"{k} = :{k}" for k in query.datos.keys())
    sql = f"UPDATE {query.tabla} SET {set_clause} WHERE {query.condicion}"

    start = time.time()
    try:
        result = db.execute(
            text(sql).execution_options(timeout=DB_TIMEOUT),
            query.datos,
        )
        db.commit()
        log_slow_query(time.time() - start, sql)
        return {
            "message":       f"Registros actualizados correctamente en '{query.tabla}'.",
            "affected_rows": result.rowcount,
        }

    except Exception as err:
        db.rollback()
        if _is_timeout(err):
            log_slow_query(time.time() - start, f"{sql}  [TIMEOUT]")
            raise HTTPException(status_code=408, detail="Timeout al ejecutar el UPDATE.")
        raise HTTPException(status_code=400, detail=str(err))


# ─────────────────────────────────────────────────────────────────────────────
# POST /execute-stored-procedure — Stored Procedure
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/execute-stored-procedure",
    summary="Ejecutar Stored Procedure",
    description=(
        "Ejecuta un stored procedure con parámetros opcionales. "
        "Maneja múltiples resultsets y devuelve el último junto con el conteo total."
    ),
)
async def execute_stored_procedure(
    sp: ExecuteStoredProcedure,
    db: Session = Depends(get_db),
):
    params = sp.parameters or {}

    if params:
        params_str = ", ".join(f"@{k} = :{k}" for k in params.keys())
        sql = f"EXEC {sp.procedure_name} {params_str}"
    else:
        sql = f"EXEC {sp.procedure_name}"

    start = time.time()
    try:
        # Usamos el cursor raw para manejar múltiples resultsets
        raw_conn = db.connection().connection
        cursor   = raw_conn.cursor()
        cursor.execute(sql, list(params.values()) if params else [])

        all_datasets: list[list[dict]] = []
        resultset_count = 0

        # Iteramos todos los resultsets con nextset()
        while True:
            if cursor.description:
                cols = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                all_datasets.append([dict(zip(cols, row)) for row in rows])
                resultset_count += 1

            if not cursor.nextset():
                break

        raw_conn.commit()
        log_slow_query(time.time() - start, sql)

        return {
            "message":          "Stored procedure ejecutado correctamente.",
            "procedure_name":   sp.procedure_name,
            "data":             all_datasets[-1] if all_datasets else None,
            "total_resultsets": resultset_count,
        }

    except Exception as err:
        try:
            raw_conn.rollback()
        except Exception:
            pass
        if _is_timeout(err):
            log_slow_query(time.time() - start, f"{sql}  [TIMEOUT]")
            raise HTTPException(status_code=408, detail="Timeout al ejecutar el stored procedure.")
        raise HTTPException(
            status_code=400,
            detail=f"Error al ejecutar '{sp.procedure_name}': {str(err)}",
        )
