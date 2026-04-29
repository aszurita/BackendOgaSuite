import logging
from app.models.casos_uso import (
    CasoUso, CasoUsoCreate, CasoUsoUpdate,
    Fuente, FuenteCreate, Subdominio, ContadoresEstado,
)
from app.models.common import PaginatedResponse
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


def _row_to_caso(row: dict) -> CasoUso:
    return CasoUso(
        id_caso_uso=row.get("id_caso_uso") or 0,
        descripcion_caso_uso=row.get("descripcion_caso_uso"),
        id_dominio=row.get("id_dominio"),
        subdominio=row.get("subdominio"),
        objetivo=row.get("objetivo"),
        estado=row.get("estado"),
        responsable=row.get("responsable"),
        fecha_inicio=row.get("fecha_inicio"),
        fecha_fin=row.get("fecha_fin"),
        sn_activo=bool(row.get("sn_activo", True)),
        fecha_creacion=row.get("fecha_creacion"),
    )


def get_casos_uso(
    conn,
    id_dominio: int | None = None,
    subdominio: str | None = None,
    buscar: str | None = None,
    estado: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[CasoUso]:
    conditions = ["sn_activo = 1"]
    params: list = []

    if id_dominio:
        conditions.append("id_dominio = %s")
        params.append(id_dominio)
    if subdominio:
        conditions.append("UPPER(IFNULL(subdominio,'')) = UPPER(%s)")
        params.append(subdominio)
    if buscar:
        conditions.append("UPPER(IFNULL(descripcion_caso_uso,'')) LIKE UPPER(%s)")
        params.append(f"%{buscar}%")
    if estado:
        conditions.append("UPPER(IFNULL(estado,'')) LIKE UPPER(%s)")
        params.append(f"%{estado}%")

    where = " AND ".join(conditions)
    offset = (page - 1) * page_size

    with conn.cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(1) AS total FROM t_casos_uso_analitica WHERE {where}",
            params,
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            f"""
            SELECT id_caso_uso, descripcion_caso_uso, id_dominio, subdominio,
                   objetivo, estado, responsable, fecha_inicio, fecha_fin,
                   sn_activo, fecha_creacion
            FROM t_casos_uso_analitica
            WHERE {where}
            ORDER BY subdominio, descripcion_caso_uso
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset],
        )
        rows = cursor.fetchall()

    return PaginatedResponse.build(
        data=[_row_to_caso(r) for r in rows], total=total, page=page, page_size=page_size
    )


def get_caso_by_id(conn, caso_id: int) -> CasoUso:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id_caso_uso, descripcion_caso_uso, id_dominio, subdominio,
                   objetivo, estado, responsable, fecha_inicio, fecha_fin,
                   sn_activo, fecha_creacion
            FROM t_casos_uso_analitica WHERE id_caso_uso = %s
            """,
            [caso_id],
        )
        row = cursor.fetchone()
    if not row:
        raise NotFoundException(f"Caso de uso id={caso_id} no encontrado")
    return _row_to_caso(row)


def crear_caso_uso(conn, data: CasoUsoCreate) -> CasoUso:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO t_casos_uso_analitica
                (descripcion_caso_uso, id_dominio, subdominio, objetivo,
                 estado, responsable, fecha_inicio, fecha_fin, sn_activo, fecha_creacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, NOW())
            """,
            [
                data.descripcion_caso_uso, data.id_dominio, data.subdominio,
                data.objetivo, data.estado, data.responsable,
                data.fecha_inicio, data.fecha_fin,
            ],
        )
        new_id = cursor.lastrowid
    return get_caso_by_id(conn, new_id)


def actualizar_caso_uso(conn, caso_id: int, data: CasoUsoUpdate) -> CasoUso:
    get_caso_by_id(conn, caso_id)
    updates, params = [], []
    for field, col in [
        ("descripcion_caso_uso", "descripcion_caso_uso"),
        ("subdominio", "subdominio"),
        ("objetivo", "objetivo"),
        ("estado", "estado"),
        ("responsable", "responsable"),
        ("fecha_inicio", "fecha_inicio"),
        ("fecha_fin", "fecha_fin"),
    ]:
        val = getattr(data, field, None)
        if val is not None:
            updates.append(f"{col} = %s")
            params.append(val)
    if not updates:
        return get_caso_by_id(conn, caso_id)
    params.append(caso_id)
    with conn.cursor() as cursor:
        cursor.execute(
            f"UPDATE t_casos_uso_analitica SET {', '.join(updates)} WHERE id_caso_uso = %s",
            params,
        )
    return get_caso_by_id(conn, caso_id)


def desactivar_caso_uso(conn, caso_id: int) -> None:
    get_caso_by_id(conn, caso_id)
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE t_casos_uso_analitica SET sn_activo = 0 WHERE id_caso_uso = %s",
            [caso_id],
        )


def get_fuentes_caso_uso(conn, caso_id: int) -> list[Fuente]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, id_fuente_aprovisionamiento, txt_tabla, descripcion, tipo_fuente
            FROM t_casos_uso_fuentes
            WHERE id_caso_uso = %s
            ORDER BY txt_tabla
            """,
            [caso_id],
        )
        return [
            Fuente(
                id=r["id"],
                id_fuente_aprovisionamiento=r.get("id_fuente_aprovisionamiento"),
                txt_tabla=r.get("txt_tabla"),
                descripcion=r.get("descripcion"),
                tipo_fuente=r.get("tipo_fuente"),
            )
            for r in cursor.fetchall()
        ]


def agregar_fuente(conn, caso_id: int, data: FuenteCreate) -> Fuente:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO t_casos_uso_fuentes
                (id_caso_uso, id_fuente_aprovisionamiento, txt_tabla, descripcion, tipo_fuente)
            VALUES (%s, %s, %s, %s, %s)
            """,
            [caso_id, data.id_fuente_aprovisionamiento, data.txt_tabla, data.descripcion, data.tipo_fuente],
        )
        new_id = cursor.lastrowid
    return Fuente(
        id=new_id,
        id_fuente_aprovisionamiento=data.id_fuente_aprovisionamiento,
        txt_tabla=data.txt_tabla,
        descripcion=data.descripcion,
        tipo_fuente=data.tipo_fuente,
    )


def eliminar_fuente(conn, caso_id: int, fuente_id: int) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            "DELETE FROM t_casos_uso_fuentes WHERE id = %s AND id_caso_uso = %s",
            [fuente_id, caso_id],
        )


def get_terminos_caso_uso(conn, caso_id: int) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT t.id, t.nombre, t.tipo, t.descripcion
            FROM t_casos_uso_terminos_mb r
            JOIN T_terminos t ON t.id = r.id_termino
            WHERE r.id_caso_uso = %s AND r.SN_ACTIVO = 1 AND t.sn_activo = 1
            ORDER BY t.nombre
            """,
            [caso_id],
        )
        return list(cursor.fetchall())


def get_subdominios(conn, id_dominio: int | None = None) -> list[Subdominio]:
    params: list = []
    where = "sn_activo = 1"
    if id_dominio:
        where += " AND id_dominio = %s"
        params.append(id_dominio)
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id_subdominio, descripcion_subdominio, id_dominio, responsable, estado, sn_activo
            FROM t_subdominios WHERE {where}
            ORDER BY descripcion_subdominio
            """,
            params,
        )
        return [
            Subdominio(
                id_subdominio=r["id_subdominio"],
                descripcion_subdominio=r.get("descripcion_subdominio"),
                id_dominio=r.get("id_dominio"),
                responsable=r.get("responsable"),
                estado=r.get("estado"),
                sn_activo=bool(r.get("sn_activo")),
            )
            for r in cursor.fetchall()
        ]


def get_contadores_estado(conn, id_dominio: int | None = None) -> ContadoresEstado:
    params: list = []
    where = "sn_activo = 1"
    if id_dominio:
        where += " AND id_dominio = %s"
        params.append(id_dominio)
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                SUM(CASE WHEN UPPER(IFNULL(estado,'')) NOT LIKE '%cerrado%' THEN 1 ELSE 0 END) AS activos,
                SUM(CASE WHEN UPPER(IFNULL(estado,'')) LIKE '%cerrado%' THEN 1 ELSE 0 END) AS terminados,
                COUNT(1) AS total
            FROM t_casos_uso_analitica WHERE {where}
            """,
            params,
        )
        row = cursor.fetchone()
    return ContadoresEstado(
        activos=row["activos"] or 0,
        terminados=row["terminados"] or 0,
        total=row["total"] or 0,
    )
