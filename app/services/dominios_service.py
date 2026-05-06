import logging
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
        nombre_dominio=row.get("descripcion_dominio"),
        concepto_clave=row.get("concepto_clave"),
        descripcion=row.get("descripcion"),
        com=row.get("com"),
        impact=row.get("impact"),
        tipo=row.get("tipo"),
        tipo_dominio=row.get("tipo"),
        familia=row.get("familia"),
        lider_sugerido=row.get("lider_sugerido"),
        atributos_basicos=row.get("atributos_basicos"),
        id_tipo_dominio=row.get("id_tipo_dominio"),
        id_tipo_familia=row.get("id_tipo_familia"),
        porcentaje_avance=row.get("porcentaje_avance"),
        codificacion=row.get("codigo_dominio"),
        cod_dominio=row.get("codigo_dominio"),
        concepto=row.get("descripcion"),
        sn_activo=bool(row.get("sn_activo", True)),
    )


def get_dominios(conn, activos_only: bool = True) -> list[Dominio]:
    where = "WHERE sn_activo = 1" if activos_only else ""
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id_dominio, codigo_Dominio AS codigo_dominio, descripcion_dominio,
                   Conceptos_Clave AS concepto_clave, descripcion,
                   COM AS com, IMPACT AS impact, Tipo AS tipo,
                   Familia_de_Dominios AS familia, lider_sugerido,
                   atributos_basicos, id_tipo_dominio, id_tipo_familia,
                   PORC_AVANCE AS porcentaje_avance, sn_activo
            FROM t_mapa_dominios {where}
            ORDER BY descripcion_dominio
            """
        )
        return [_row_to_dominio(r) for r in cursor.fetchall()]


def get_dominio_by_id(conn, dominio_id: int) -> Dominio:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id_dominio, codigo_Dominio AS codigo_dominio, descripcion_dominio,
                   Conceptos_Clave AS concepto_clave, descripcion,
                   COM AS com, IMPACT AS impact, Tipo AS tipo,
                   Familia_de_Dominios AS familia, lider_sugerido,
                   atributos_basicos, id_tipo_dominio, id_tipo_familia,
                   PORC_AVANCE AS porcentaje_avance, sn_activo
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


def _count_tablas_by_dominio_id(conn, dominio_id: int) -> int:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(DISTINCT CONCAT(d.id_fuente_aprovisionamiento, '|', d.txt_desc_tabla)) AS total
            FROM t_dominios_tablas_oficiales d
            JOIN t_fuente_aprovisionamiento f
              ON f.id_fuente_aprovisionamiento = d.id_fuente_aprovisionamiento
            WHERE d.id_dominio_asociado = %s
              AND f.sn_activo = 1
            """,
            [dominio_id],
        )
        return cursor.fetchone()["total"]


def _count_avances(conn, dominio_id: int) -> tuple[int, int]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(1) AS total,
                   SUM(CASE WHEN estado_paso IN ('Completado', 'No aplica') THEN 1 ELSE 0 END) AS completados
            FROM t_avances_dominio
            WHERE id_dominio=%s
            """,
            [dominio_id],
        )
        row = cursor.fetchone()
    return (row["total"] or 0), (row["completados"] or 0)


async def get_estadisticas(conn, dominio_id: int) -> DominioStats:
    dominio = get_dominio_by_id(conn, dominio_id)
    nombre = dominio.descripcion_dominio or ""

    casos = _count_casos(conn, dominio_id)
    terminos, atributos = _count_terminos(conn, nombre)
    artefactos = _count_artefactos(conn, dominio_id)
    estructura = _count_estructura(conn, dominio_id)
    tablas = _count_tablas_by_dominio_id(conn, dominio_id)
    av_total, av_comp = _count_avances(conn, dominio_id)

    if dominio.porcentaje_avance is not None:
        avance = float(dominio.porcentaje_avance)
        porc = round(avance * 100, 1) if avance <= 1 else round(avance, 1)
    else:
        porc = round(av_comp / av_total * 100, 1) if av_total > 0 else 0.0
    return DominioStats(
        cant_casos=casos, cant_terminos=terminos, cant_atributos=atributos,
        cant_artefactos=artefactos, cant_tablas=tablas, cant_estructura=estructura,
        porc_avance=porc,
    )


def get_tablas_oficiales(conn, dominio_id: int) -> list[dict]:
    get_dominio_by_id(conn, dominio_id)
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT
                t.id_fuente_aprovisionamiento AS id,
                t.id_fuente_aprovisionamiento,
                t.txt_desc_tabla,
                t.txt_desc_tabla AS tabla,
                NULL AS plataforma,
                f.txt_servidor AS servidor,
                f.txt_host AS `base`,
                f.txt_fuente_esquema AS esquema,
                f.txt_fuente_aprovisionamiento AS fuente,
                t.descripcion_tabla,
                t.descripcion_tabla AS descripcion,
                t.data_owner,
                t.nombre_data_owner,
                t.data_steward,
                t.nombre_data_steward,
                t.id_clasificacion,
                t.etiquetas,
                t.avance,
                d.id_dominio_asociado AS id_dominio
            FROM t_tablas_oficiales t
            JOIN t_dominios_tablas_oficiales d
              ON d.id_fuente_aprovisionamiento = t.id_fuente_aprovisionamiento
             AND d.txt_desc_tabla = t.txt_desc_tabla
            JOIN t_fuente_aprovisionamiento f
              ON f.id_fuente_aprovisionamiento = t.id_fuente_aprovisionamiento
            WHERE d.id_dominio_asociado = %s
              AND f.sn_activo = 1
            ORDER BY f.txt_servidor, f.txt_host, f.txt_fuente_esquema, t.txt_desc_tabla
            """,
            [dominio_id],
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
            """
            SELECT id_paso AS id_avance, txt_desc_paso AS descripcion, estado_paso
            FROM t_avances_dominio
            WHERE id_dominio=%s
            ORDER BY id_paso
            """,
            [dominio_id],
        )
        return [
            AvanceDominio(
                id_avance=r["id_avance"],
                descripcion=r.get("descripcion"),
                completado=r.get("estado_paso") in ("Completado", "No aplica"),
            )
            for r in cursor.fetchall()
        ]


def actualizar_avance(conn, dominio_id: int, item_id: int, data: AvanceUpdate) -> AvanceDominio:
    with conn.cursor() as cursor:
        if data.completado:
            cursor.execute(
                """
                UPDATE t_avances_dominio
                SET estado_paso='Completado', porcentaje_avance_orig=1
                WHERE id_paso=%s AND id_dominio=%s
                """,
                [item_id, dominio_id],
            )
        else:
            cursor.execute(
                """
                UPDATE t_avances_dominio
                SET estado_paso='En proceso', porcentaje_avance_orig=0
                WHERE id_paso=%s AND id_dominio=%s
                """,
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
                (codigo_Dominio, descripcion_dominio, Conceptos_Clave, descripcion,
                 COM, IMPACT, Tipo, Familia_de_Dominios, lider_sugerido,
                 atributos_basicos, id_tipo_dominio, id_tipo_familia, sn_activo, PORC_AVANCE)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s)
            """,
            [
                data.codigo_dominio or data.cod_dominio or data.codificacion or "",
                data.descripcion_dominio,
                data.concepto_clave or data.concepto,
                data.descripcion,
                data.com if data.com is not None else 0,
                data.impact if data.impact is not None else 0,
                data.tipo or data.tipo_dominio or "",
                data.familia or "",
                data.lider_sugerido,
                data.atributos_basicos,
                data.id_tipo_dominio,
                data.id_tipo_familia,
                data.porcentaje_avance if data.porcentaje_avance is not None else 0,
            ],
        )
        new_id = cursor.lastrowid
    return get_dominio_by_id(conn, new_id)


def actualizar_dominio(conn, dominio_id: int, data: DominioUpdate) -> Dominio:
    get_dominio_by_id(conn, dominio_id)
    updates, params = [], []
    updated_cols = set()
    for field, col in [
        ("codigo_dominio", "codigo_Dominio"), ("cod_dominio", "codigo_Dominio"),
        ("codificacion", "codigo_Dominio"),
        ("descripcion_dominio", "descripcion_dominio"), ("nombre_dominio", "descripcion_dominio"),
        ("concepto_clave", "Conceptos_Clave"), ("concepto", "descripcion"),
        ("descripcion", "descripcion"), ("com", "COM"), ("impact", "IMPACT"),
        ("tipo", "Tipo"), ("tipo_dominio", "Tipo"),
        ("familia", "Familia_de_Dominios"), ("lider_sugerido", "lider_sugerido"),
        ("atributos_basicos", "atributos_basicos"),
        ("id_tipo_dominio", "id_tipo_dominio"), ("id_tipo_familia", "id_tipo_familia"),
        ("porcentaje_avance", "PORC_AVANCE"),
    ]:
        val = getattr(data, field, None)
        if val is not None and col not in updated_cols:
            updates.append(f"{col} = %s")
            params.append(val)
            updated_cols.add(col)
    if not updates:
        return get_dominio_by_id(conn, dominio_id)
    params.append(dominio_id)
    with conn.cursor() as cursor:
        cursor.execute(
            f"UPDATE t_mapa_dominios SET {', '.join(updates)} WHERE id_dominio=%s", params
        )
    return get_dominio_by_id(conn, dominio_id)
