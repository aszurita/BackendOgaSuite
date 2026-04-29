import logging
from app.models.terminos import (
    Termino, TerminoCreate, TerminoUpdate, TerminoResumen,
    DominioMapa, BuscarDuplicadoResponse,
)
from app.models.common import PaginatedResponse
from app.core.exceptions import NotFoundException, ConflictException

logger = logging.getLogger(__name__)


def _row_to_termino(row: dict) -> Termino:
    return Termino(
        id=row.get("id") or 0,
        nombre=row.get("nombre") or "",
        tipo=row.get("tipo") or "TERMINO",
        descripcion=row.get("descripcion"),
        dominios=row.get("dominios"),
        casos_uso=row.get("casos_uso"),
        caracteristicas=row.get("caracteristicas"),
        txt_desc_subcategoria=row.get("txt_desc_subcategoria"),
        dato_personal=row.get("dato_personal"),
        golden_record=bool(row.get("golden_record")),
        catalogos_asociados=row.get("catalogos_asociados"),
        etiqueta_tecnica=row.get("etiqueta_tecnica"),
        prioridad=row.get("prioridad"),
        sn_activo=bool(row.get("sn_activo", True)),
        fecha_creacion=row.get("fecha_creacion"),
        fecha_modificacion=row.get("fecha_modificacion"),
        autor_creacion=row.get("autor_creacion"),
        autor_modificacion=row.get("autor_modificacion"),
    )


def _build_where(
    buscar, tipo, dominio, golden_record, dato_personal, caracteristica
) -> tuple[str, list]:
    conditions = ["sn_activo = 1"]
    params: list = []

    if buscar:
        conditions.append(
            "(UPPER(nombre) LIKE UPPER(%s) OR UPPER(IFNULL(descripcion,'')) LIKE UPPER(%s))"
        )
        t = f"%{buscar}%"
        params += [t, t]
    if tipo:
        conditions.append("tipo = %s")
        params.append(tipo)
    if dominio:
        conditions.append("LOCATE(%s, IFNULL(dominios,'')) > 0")
        params.append(dominio)
    if golden_record is not None:
        conditions.append("golden_record = %s")
        params.append(1 if golden_record else 0)
    if dato_personal is not None:
        conditions.append("dato_personal = %s")
        params.append(dato_personal)
    if caracteristica:
        conditions.append("UPPER(IFNULL(caracteristicas,'')) LIKE UPPER(%s)")
        params.append(f"%{caracteristica}%")

    return " AND ".join(conditions), params


def get_terminos(conn, page=1, page_size=20, buscar=None, tipo=None,
                 dominio=None, golden_record=None, dato_personal=None,
                 caracteristica=None) -> PaginatedResponse[Termino]:
    where, params = _build_where(buscar, tipo, dominio, golden_record, dato_personal, caracteristica)
    offset = (page - 1) * page_size

    with conn.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(1) AS total FROM T_terminos WHERE {where}", params)
        total = cursor.fetchone()["total"]

        cursor.execute(
            f"""
            SELECT id, nombre, tipo, descripcion, dominios, casos_uso, caracteristicas,
                   txt_desc_subcategoria, dato_personal, golden_record,
                   catalogos_asociados, etiqueta_tecnica, prioridad,
                   sn_activo, fecha_creacion, fecha_modificacion,
                   autor_creacion, autor_modificacion
            FROM T_terminos
            WHERE {where}
            ORDER BY COALESCE(fecha_modificacion, fecha_creacion) DESC
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset],
        )
        rows = cursor.fetchall()

    return PaginatedResponse.build(
        data=[_row_to_termino(r) for r in rows], total=total, page=page, page_size=page_size
    )


def get_terminos_recientes(conn, limit: int = 10) -> list[Termino]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, nombre, tipo, descripcion, dominios, casos_uso, caracteristicas,
                   txt_desc_subcategoria, dato_personal, golden_record,
                   catalogos_asociados, etiqueta_tecnica, prioridad,
                   sn_activo, fecha_creacion, fecha_modificacion,
                   autor_creacion, autor_modificacion
            FROM T_terminos
            WHERE sn_activo = 1
            ORDER BY COALESCE(fecha_modificacion, fecha_creacion) DESC
            LIMIT %s
            """,
            [limit],
        )
        return [_row_to_termino(r) for r in cursor.fetchall()]


def get_termino_by_id(conn, termino_id: int) -> Termino:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, nombre, tipo, descripcion, dominios, casos_uso, caracteristicas,
                   txt_desc_subcategoria, dato_personal, golden_record,
                   catalogos_asociados, etiqueta_tecnica, prioridad,
                   sn_activo, fecha_creacion, fecha_modificacion,
                   autor_creacion, autor_modificacion
            FROM T_terminos WHERE id = %s
            """,
            [termino_id],
        )
        row = cursor.fetchone()
    if not row:
        raise NotFoundException(f"Termino id={termino_id} no encontrado")
    return _row_to_termino(row)


def buscar_duplicado(conn, nombre: str, tipo: str,
                     exclude_id: int | None = None) -> BuscarDuplicadoResponse:
    with conn.cursor() as cursor:
        if exclude_id:
            cursor.execute(
                "SELECT id FROM T_terminos WHERE UPPER(nombre)=UPPER(%s) AND tipo=%s AND sn_activo=1 AND id<>%s",
                [nombre, tipo, exclude_id],
            )
        else:
            cursor.execute(
                "SELECT id FROM T_terminos WHERE UPPER(nombre)=UPPER(%s) AND tipo=%s AND sn_activo=1",
                [nombre, tipo],
            )
        row = cursor.fetchone()
    return BuscarDuplicadoResponse(
        es_duplicado=bool(row),
        termino_existente_id=row["id"] if row else None,
    )


def crear_termino(conn, data: TerminoCreate, autor_codigo: int | None) -> Termino:
    dup = buscar_duplicado(conn, data.nombre, data.tipo)
    if dup.es_duplicado:
        raise ConflictException(f"Ya existe '{data.nombre}' con tipo '{data.tipo}'")

    golden_val = 1 if data.golden_record else 0
    subcategoria = data.txt_desc_subcategoria
    if data.tipo in ("ATRIBUTO", "ATRIBUTO/TERMINO") and not subcategoria:
        subcategoria = "EN REVISIÓN"

    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO T_terminos
                (nombre, tipo, descripcion, dominios, casos_uso, caracteristicas,
                 txt_desc_subcategoria, dato_personal, golden_record,
                 catalogos_asociados, etiqueta_tecnica, prioridad,
                 sn_activo, fecha_creacion, autor_creacion)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,NOW(),%s)
            """,
            [data.nombre, data.tipo, data.descripcion, data.dominios, data.casos_uso,
             data.caracteristicas, subcategoria, data.dato_personal, golden_val,
             data.catalogos_asociados, data.etiqueta_tecnica, data.prioridad, autor_codigo],
        )
        new_id = cursor.lastrowid
    return get_termino_by_id(conn, new_id)


def actualizar_termino(conn, termino_id: int, data: TerminoUpdate,
                       autor_codigo: int | None) -> Termino:
    get_termino_by_id(conn, termino_id)
    updates, params = [], []

    for field, col in [
        ("nombre", "nombre"), ("tipo", "tipo"), ("descripcion", "descripcion"),
        ("dominios", "dominios"), ("casos_uso", "casos_uso"),
        ("caracteristicas", "caracteristicas"),
        ("txt_desc_subcategoria", "txt_desc_subcategoria"),
        ("dato_personal", "dato_personal"),
        ("catalogos_asociados", "catalogos_asociados"),
        ("etiqueta_tecnica", "etiqueta_tecnica"), ("prioridad", "prioridad"),
    ]:
        val = getattr(data, field, None)
        if val is not None:
            updates.append(f"{col} = %s")
            params.append(val)

    if data.golden_record is not None:
        updates.append("golden_record = %s")
        params.append(1 if data.golden_record else 0)

    if not updates:
        return get_termino_by_id(conn, termino_id)

    updates += ["fecha_modificacion = NOW()", "autor_modificacion = %s"]
    params += [autor_codigo, termino_id]

    with conn.cursor() as cursor:
        cursor.execute(
            f"UPDATE T_terminos SET {', '.join(updates)} WHERE id = %s", params
        )
    return get_termino_by_id(conn, termino_id)


def desactivar_termino(conn, termino_id: int, motivo: str | None,
                       autor_codigo: int | None) -> None:
    get_termino_by_id(conn, termino_id)
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE T_terminos SET sn_activo=0, fecha_modificacion=NOW(), autor_modificacion=%s WHERE id=%s",
            [autor_codigo, termino_id],
        )


def get_casos_uso_del_termino(conn, termino_id: int) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT r.id_caso_uso, c.descripcion_caso_uso AS descripcion
            FROM t_casos_uso_terminos_mb r
            JOIN t_casos_uso_analitica c ON c.id_caso_uso = r.id_caso_uso
            WHERE r.id_termino = %s AND r.SN_ACTIVO = 1 AND c.sn_activo = 1
            """,
            [termino_id],
        )
        return list(cursor.fetchall())


def sync_casos_uso(conn, termino_id: int, casos_ids: list[int],
                   autor_codigo: int | None) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id_caso_uso, SN_ACTIVO FROM t_casos_uso_terminos_mb WHERE id_termino = %s",
            [termino_id],
        )
        existentes = {r["id_caso_uso"]: bool(r["SN_ACTIVO"]) for r in cursor.fetchall()}

    seleccionados = set(casos_ids)

    with conn.cursor() as cursor:
        for caso_id in seleccionados:
            if caso_id in existentes:
                if not existentes[caso_id]:
                    cursor.execute(
                        "UPDATE t_casos_uso_terminos_mb SET SN_ACTIVO=1 WHERE id_termino=%s AND id_caso_uso=%s",
                        [termino_id, caso_id],
                    )
            else:
                cursor.execute(
                    "INSERT INTO t_casos_uso_terminos_mb (id_termino, id_caso_uso, SN_ACTIVO) VALUES (%s,%s,1)",
                    [termino_id, caso_id],
                )

        for caso_id, activo in existentes.items():
            if caso_id not in seleccionados and activo:
                cursor.execute(
                    "UPDATE t_casos_uso_terminos_mb SET SN_ACTIVO=0 WHERE id_termino=%s AND id_caso_uso=%s",
                    [termino_id, caso_id],
                )


def get_dominios_mapa(conn) -> list[DominioMapa]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT d.descripcion_dominio, COUNT(t.id) AS total
            FROM t_mapa_dominios d
            LEFT JOIN T_terminos t
                ON t.sn_activo = 1
                AND LOCATE(d.descripcion_dominio, IFNULL(t.dominios,'')) > 0
            WHERE d.sn_activo = 1
            GROUP BY d.descripcion_dominio
            ORDER BY total DESC
            """
        )
        return [DominioMapa(dominio=r["descripcion_dominio"], count=r["total"])
                for r in cursor.fetchall()]


def get_crosslinks(conn) -> list[TerminoResumen]:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, nombre, tipo FROM T_terminos WHERE sn_activo=1 ORDER BY LENGTH(nombre) DESC"
        )
        return [TerminoResumen(id=r["id"], nombre=r["nombre"], tipo=r["tipo"])
                for r in cursor.fetchall()]
