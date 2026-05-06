import logging
from app.models.casos_uso import (
    CasoUso, CasoUsoCreate, CasoUsoUpdate,
    Fuente, FuenteCreate, Subdominio, ContadoresEstado,
)
from app.models.common import PaginatedResponse
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


def _to_str(value) -> str | None:
    return None if value is None else str(value)


def _row_to_caso(row: dict) -> CasoUso:
    estado = row.get("estado") or row.get("estado_caso_uso")
    detalle = row.get("detalle_caso_uso")
    responsable = row.get("responsable") or row.get("cod_ingeniero_responsable")
    fecha_creacion = row.get("fecha_creacion") or row.get("fec_creacion")
    return CasoUso(
        id_caso_uso=row.get("id_caso_uso") or 0,
        descripcion_caso_uso=row.get("descripcion_caso_uso"),
        detalle_caso_uso=detalle,
        entregable_caso_uso=row.get("entregable_caso_uso"),
        id_dominio=row.get("id_dominio"),
        subdominio=row.get("subdominio"),
        objetivo=row.get("objetivo") or detalle,
        estado=estado,
        estado_caso_uso=estado,
        responsable=_to_str(responsable),
        cod_especialista=_to_str(row.get("cod_especialista")),
        cod_sponsor=_to_str(row.get("cod_sponsor")),
        cod_ingeniero_responsable=_to_str(row.get("cod_ingeniero_responsable")),
        cod_translator=_to_str(row.get("cod_translator")),
        tipo_iniciativa=row.get("tipo_iniciativa"),
        fecha_inicio=row.get("fecha_inicio"),
        fecha_fin=row.get("fecha_fin"),
        sn_activo=bool(row.get("sn_activo", True)),
        fecha_creacion=fecha_creacion,
        fec_creacion=fecha_creacion,
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
        conditions.append("UPPER(IFNULL(SUBDOMINIO,'')) = UPPER(%s)")
        params.append(subdominio)
    if buscar:
        conditions.append(
            "(UPPER(IFNULL(descripcion_caso_uso,'')) LIKE UPPER(%s) "
            "OR UPPER(IFNULL(detalle_caso_uso,'')) LIKE UPPER(%s) "
            "OR UPPER(IFNULL(entregable_caso_uso,'')) LIKE UPPER(%s))"
        )
        params += [f"%{buscar}%", f"%{buscar}%", f"%{buscar}%"]
    if estado:
        conditions.append("UPPER(IFNULL(estado_caso_uso,'')) LIKE UPPER(%s)")
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
            SELECT id_caso_uso, descripcion_caso_uso, detalle_caso_uso,
                   entregable_caso_uso, id_dominio, SUBDOMINIO AS subdominio,
                   cod_especialista, cod_sponsor, cod_ingeniero_responsable,
                   estado_caso_uso AS estado, estado_caso_uso,
                   tipo_iniciativa, sn_activo, fec_creacion
            FROM t_casos_uso_analitica
            WHERE {where}
            ORDER BY SUBDOMINIO, descripcion_caso_uso
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
            SELECT id_caso_uso, descripcion_caso_uso, detalle_caso_uso,
                   entregable_caso_uso, id_dominio, SUBDOMINIO AS subdominio,
                   cod_especialista, cod_sponsor, cod_ingeniero_responsable,
                   estado_caso_uso AS estado, estado_caso_uso,
                   tipo_iniciativa, sn_activo, fec_creacion
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
                (descripcion_caso_uso, detalle_caso_uso, entregable_caso_uso,
                 id_dominio, SUBDOMINIO, cod_especialista, cod_sponsor,
                 cod_ingeniero_responsable, estado_caso_uso, tipo_iniciativa,
                 sn_activo, fec_creacion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, NOW())
            """,
            [
                data.descripcion_caso_uso,
                data.detalle_caso_uso or data.objetivo,
                data.entregable_caso_uso,
                data.id_dominio,
                data.subdominio,
                data.cod_especialista,
                data.cod_sponsor,
                data.cod_ingeniero_responsable or data.responsable,
                data.estado_caso_uso or data.estado,
                data.tipo_iniciativa,
            ],
        )
        new_id = cursor.lastrowid
    return get_caso_by_id(conn, new_id)


def actualizar_caso_uso(conn, caso_id: int, data: CasoUsoUpdate) -> CasoUso:
    get_caso_by_id(conn, caso_id)
    updates, params = [], []
    updated_cols = set()
    for field, col in [
        ("descripcion_caso_uso", "descripcion_caso_uso"),
        ("detalle_caso_uso", "detalle_caso_uso"),
        ("objetivo", "detalle_caso_uso"),
        ("entregable_caso_uso", "entregable_caso_uso"),
        ("subdominio", "SUBDOMINIO"),
        ("estado", "estado_caso_uso"),
        ("estado_caso_uso", "estado_caso_uso"),
        ("responsable", "cod_ingeniero_responsable"),
        ("cod_especialista", "cod_especialista"),
        ("cod_sponsor", "cod_sponsor"),
        ("cod_ingeniero_responsable", "cod_ingeniero_responsable"),
        ("tipo_iniciativa", "tipo_iniciativa"),
    ]:
        val = getattr(data, field, None)
        if val is not None and col not in updated_cols:
            updates.append(f"{col} = %s")
            params.append(val)
            updated_cols.add(col)
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
    get_caso_by_id(conn, caso_id)
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id_fuente, clave_fuente, sn_activo
            FROM t_casos_uso_fuentes
            WHERE id_caso_uso = %s AND sn_activo = 1
            ORDER BY clave_fuente
            """,
            [caso_id],
        )
        return [
            Fuente(
                id=r["id_fuente"],
                id_fuente=r["id_fuente"],
                clave_fuente=r.get("clave_fuente"),
                txt_tabla=r.get("clave_fuente"),
                sn_activo=bool(r.get("sn_activo")),
            )
            for r in cursor.fetchall()
        ]


def agregar_fuente(conn, caso_id: int, data: FuenteCreate) -> Fuente:
    get_caso_by_id(conn, caso_id)
    clave_fuente = data.clave_fuente or data.txt_tabla or str(data.id_fuente_aprovisionamiento)
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO t_casos_uso_fuentes
                (id_caso_uso, clave_fuente, sn_activo, fec_creacion)
            VALUES (%s, %s, 1, NOW())
            """,
            [caso_id, clave_fuente],
        )
        new_id = cursor.lastrowid
    return Fuente(
        id=new_id,
        id_fuente=new_id,
        id_fuente_aprovisionamiento=data.id_fuente_aprovisionamiento,
        clave_fuente=clave_fuente,
        txt_tabla=clave_fuente,
    )


def eliminar_fuente(conn, caso_id: int, fuente_id: int) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE t_casos_uso_fuentes SET sn_activo = 0, fec_modificacion = NOW() WHERE id_fuente = %s AND id_caso_uso = %s",
            [fuente_id, caso_id],
        )


def get_terminos_caso_uso(conn, caso_id: int) -> list[dict]:
    get_caso_by_id(conn, caso_id)
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT t.id, t.nombre, t.tipo, t.descripcion
            FROM t_casos_uso_terminos_mb r
            JOIN T_terminos t ON CAST(t.id AS CHAR) = r.cod_terminos
            WHERE r.id_caso_uso = %s AND r.sn_activo = 1 AND t.sn_activo = 1
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
            SELECT id_subdominio, txt_desc_subdominio, txt_obs_subdominio, id_dominio, sn_activo
            FROM t_subdominios WHERE {where}
            ORDER BY txt_desc_subdominio
            """,
            params,
        )
        return [
            Subdominio(
                id_subdominio=r["id_subdominio"],
                descripcion_subdominio=r.get("txt_desc_subdominio"),
                txt_desc_subdominio=r.get("txt_desc_subdominio"),
                txt_obs_subdominio=r.get("txt_obs_subdominio"),
                id_dominio=r.get("id_dominio"),
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
                SUM(CASE WHEN UPPER(IFNULL(estado_caso_uso,'')) NOT LIKE '%%CERRADO%%' THEN 1 ELSE 0 END) AS activos,
                SUM(CASE WHEN UPPER(IFNULL(estado_caso_uso,'')) LIKE '%%CERRADO%%' THEN 1 ELSE 0 END) AS terminados,
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
