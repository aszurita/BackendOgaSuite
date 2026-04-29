import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.models.dominios import (
    Dominio, DominioCreate, DominioUpdate, DominioStats,
    AvanceDominio, AvanceUpdate,
)
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


def _row_to_dominio(row: dict) -> Dominio:
    return Dominio(
        id_dominio=row.get("id_dominio") or 0,
        codigo_dominio=row.get("codigo_dominio"),
        descripcion_dominio=row.get("descripcion_dominio"),
        tipo_base_datos=row.get("tipo_base_datos"),
        descripcion_tipo=row.get("descripcion_tipo"),
        responsable=row.get("responsable"),
        objetivo=row.get("objetivo"),
        alcance=row.get("alcance"),
        estado=row.get("estado"),
        sn_activo=bool(row.get("sn_activo", True)),
        fecha_creacion=row.get("fecha_creacion"),
        fecha_modificacion=row.get("fecha_modificacion"),
    )


def get_dominios(conn, activos_only: bool = True) -> list[Dominio]:
    where = "WHERE sn_activo = 1" if activos_only else ""
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id_dominio, codigo_dominio, descripcion_dominio, tipo_base_datos,
                   descripcion_tipo, responsable, objetivo, alcance, estado,
                   sn_activo, fecha_creacion, fecha_modificacion
            FROM t_mapa_dominios {where}
            ORDER BY descripcion_dominio
            """
        )
        return [_row_to_dominio(r) for r in cursor.fetchall()]


def get_dominio_by_id(conn, dominio_id: int) -> Dominio:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id_dominio, codigo_dominio, descripcion_dominio, tipo_base_datos,
                   descripcion_tipo, responsable, objetivo, alcance, estado,
                   sn_activo, fecha_creacion, fecha_modificacion
            FROM t_mapa_dominios WHERE id_dominio = %s
            """,
            [dominio_id],
        )
        row = cursor.fetchone()
    if not row:
        raise NotFoundException(f"Dominio id={dominio_id} no encontrado")
    return _row_to_dominio(row)


def _count_casos(conn, dominio_id: int) -> int:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(1) AS total FROM t_casos_uso_analitica WHERE id_dominio=%s AND sn_activo=1",
            [dominio_id],
        )
        return cursor.fetchone()["total"]


def _count_terminos(conn, nombre_dominio: str) -> tuple[int, int]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT tipo, COUNT(1) AS cnt FROM T_terminos
            WHERE sn_activo=1 AND LOCATE(%s, IFNULL(dominios,'')) > 0
            GROUP BY tipo
            """,
            [nombre_dominio],
        )
        terminos, atributos = 0, 0
        for row in cursor.fetchall():
            if row["tipo"] == "TERMINO":
                terminos = row["cnt"]
            elif row["tipo"] in ("ATRIBUTO", "ATRIBUTO/TERMINO"):
                atributos += row["cnt"]
    return terminos, atributos


def _count_artefactos(conn, dominio_id: int) -> int:
    # T_ARTEFACTOS pending identification in DB — returns 0 until confirmed
    return 0


def _count_estructura(conn, dominio_id: int) -> int:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(DISTINCT usuario) AS total FROM t_estructura_dominio WHERE id_dominio=%s AND sn_activo=1",
            [dominio_id],
        )
        return cursor.fetchone()["total"]


def _count_tablas(conn, nombre_dominio: str) -> int:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(DISTINCT clave_fuente) AS total FROM t_tablas_oficiales WHERE LOCATE(%s, IFNULL(dominios,'')) > 0 AND sn_activo=1",
            [nombre_dominio],
        )
        return cursor.fetchone()["total"]


def _count_avances(conn, dominio_id: int) -> tuple[int, int]:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(1) AS total, SUM(CASE WHEN completado=1 THEN 1 ELSE 0 END) AS completados FROM t_avances_dominio WHERE id_dominio=%s",
            [dominio_id],
        )
        row = cursor.fetchone()
    return (row["total"] or 0), (row["completados"] or 0)


async def get_estadisticas(conn, dominio_id: int) -> DominioStats:
    dominio = get_dominio_by_id(conn, dominio_id)
    nombre = dominio.descripcion_dominio or ""

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=6) as executor:
        fut_c  = loop.run_in_executor(executor, _count_casos,       conn, dominio_id)
        fut_t  = loop.run_in_executor(executor, _count_terminos,    conn, nombre)
        fut_a  = loop.run_in_executor(executor, _count_artefactos,  conn, dominio_id)
        fut_e  = loop.run_in_executor(executor, _count_estructura,  conn, dominio_id)
        fut_tb = loop.run_in_executor(executor, _count_tablas,      conn, nombre)
        fut_av = loop.run_in_executor(executor, _count_avances,     conn, dominio_id)

        casos, (terminos, atributos), artefactos, estructura, tablas, (av_total, av_comp) = \
            await asyncio.gather(fut_c, fut_t, fut_a, fut_e, fut_tb, fut_av)

    porc = round(av_comp / av_total * 100, 1) if av_total > 0 else 0.0
    return DominioStats(
        cant_casos=casos, cant_terminos=terminos, cant_atributos=atributos,
        cant_artefactos=artefactos, cant_tablas=tablas, cant_estructura=estructura,
        porc_avance=porc,
    )


def get_tablas_oficiales(conn, dominio_id: int) -> list[dict]:
    dominio = get_dominio_by_id(conn, dominio_id)
    nombre = dominio.descripcion_dominio or ""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, plataforma, servidor, `base`, esquema, tabla,
                   descripcion_tabla, data_owner, nombre_data_owner
            FROM t_tablas_oficiales
            WHERE LOCATE(%s, IFNULL(dominios,'')) > 0 AND sn_activo=1
            ORDER BY tabla
            """,
            [nombre],
        )
        return list(cursor.fetchall())


def get_terminos_por_dominio(conn, dominio_id: int, tipo: str | None) -> list[dict]:
    dominio = get_dominio_by_id(conn, dominio_id)
    nombre = dominio.descripcion_dominio or ""
    params: list = [nombre]
    tipo_filter = ""
    if tipo:
        tipo_filter = " AND tipo = %s"
        params.append(tipo)
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id, nombre, tipo, descripcion, golden_record, dato_personal
            FROM T_terminos
            WHERE sn_activo=1 AND LOCATE(%s, IFNULL(dominios,'')) > 0
            {tipo_filter}
            ORDER BY nombre
            """,
            params,
        )
        return list(cursor.fetchall())


def get_avances(conn, dominio_id: int) -> list[AvanceDominio]:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id_avance, descripcion, completado, fecha_completado, responsable FROM t_avances_dominio WHERE id_dominio=%s ORDER BY id_avance",
            [dominio_id],
        )
        return [
            AvanceDominio(
                id_avance=r["id_avance"],
                descripcion=r.get("descripcion"),
                completado=bool(r.get("completado")),
                fecha_completado=r.get("fecha_completado"),
                responsable=r.get("responsable"),
            )
            for r in cursor.fetchall()
        ]


def actualizar_avance(conn, dominio_id: int, item_id: int, data: AvanceUpdate) -> AvanceDominio:
    with conn.cursor() as cursor:
        if data.completado:
            cursor.execute(
                "UPDATE t_avances_dominio SET completado=1, fecha_completado=NOW() WHERE id_avance=%s AND id_dominio=%s",
                [item_id, dominio_id],
            )
        else:
            cursor.execute(
                "UPDATE t_avances_dominio SET completado=0, fecha_completado=NULL WHERE id_avance=%s AND id_dominio=%s",
                [item_id, dominio_id],
            )
    avances = get_avances(conn, dominio_id)
    match = next((a for a in avances if a.id_avance == item_id), None)
    if not match:
        raise NotFoundException(f"Avance id={item_id} no encontrado")
    return match


def crear_dominio(conn, data: DominioCreate) -> Dominio:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO t_mapa_dominios
                (codigo_dominio, descripcion_dominio, tipo_base_datos, descripcion_tipo,
                 responsable, objetivo, alcance, estado, sn_activo, fecha_creacion)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,1,NOW())
            """,
            [data.codigo_dominio, data.descripcion_dominio, data.tipo_base_datos,
             data.descripcion_tipo, data.responsable, data.objetivo, data.alcance, data.estado],
        )
        new_id = cursor.lastrowid
    return get_dominio_by_id(conn, new_id)


def actualizar_dominio(conn, dominio_id: int, data: DominioUpdate) -> Dominio:
    get_dominio_by_id(conn, dominio_id)
    updates, params = [], []
    for field, col in [
        ("codigo_dominio", "codigo_dominio"), ("descripcion_dominio", "descripcion_dominio"),
        ("tipo_base_datos", "tipo_base_datos"), ("descripcion_tipo", "descripcion_tipo"),
        ("responsable", "responsable"), ("objetivo", "objetivo"),
        ("alcance", "alcance"), ("estado", "estado"),
    ]:
        val = getattr(data, field, None)
        if val is not None:
            updates.append(f"{col} = %s")
            params.append(val)
    if not updates:
        return get_dominio_by_id(conn, dominio_id)
    updates.append("fecha_modificacion = NOW()")
    params.append(dominio_id)
    with conn.cursor() as cursor:
        cursor.execute(
            f"UPDATE t_mapa_dominios SET {', '.join(updates)} WHERE id_dominio=%s", params
        )
    return get_dominio_by_id(conn, dominio_id)
