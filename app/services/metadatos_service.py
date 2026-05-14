import logging
import re
from datetime import datetime
from app.models.metadatos import (
    TablaOficial, TablaUpdate, Campo, CampoUpdate,
    RecomendacionDoc, ArbolMetadatos, NodoServidor, NodoBase, NodoEsquema,
    Empleado, FiltrosMetadatos,
)
from app.models.common import PaginatedResponse
from app.core.cache import (
    get_arbol_cache, get_arbol_lock, invalidar_arbol_cache,
    get_tablas_all_cache, get_tablas_all_lock, invalidar_tablas_all_cache,
)
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)

PREFIJOS_SUGERENCIA = {
    "id_":     "Identificador único de {entidad}",
    "cod_":    "Código de {entidad}",
    "txt_":    "Texto descriptivo de {entidad}",
    "flg_":    "Indicador binario de {condicion} (0=No, 1=Sí)",
    "sn_":     "Indicador binario de {condicion} (0=No, 1=Sí)",
    "fec_":    "Fecha de {evento}",
    "fecha_":  "Fecha de {evento}",
    "num_":    "Cantidad numérica de {metrica}",
    "val_":    "Valor numérico de {metrica}",
    "desc_":   "Descripción de {entidad}",
    "nom_":    "Nombre de {entidad}",
}

CLASIFICACION_MAP = {1: "OFICIAL", 2: "TRABAJO", 3: "TEMPORAL", 4: "DESUSO"}


def _row_to_tabla(row: dict) -> TablaOficial:
    id_clas = row.get("id_clasificacion")
    return TablaOficial(
        id=row.get("id") or 0,
        id_fuente_aprovisionamiento=row.get("id_fuente_aprovisionamiento"),
        txt_desc_tabla=row.get("txt_desc_tabla"),
        fuente=row.get("fuente"),
        plataforma=row.get("plataforma"),
        servidor=row.get("servidor"),
        base=row.get("base"),
        esquema=row.get("esquema"),
        tabla=row.get("tabla"),
        descripcion_tabla=row.get("descripcion_tabla"),
        data_owner=row.get("data_owner"),
        nombre_data_owner=row.get("nombre_data_owner"),
        data_steward=row.get("data_steward"),
        nombre_data_steward=row.get("nombre_data_steward"),
        id_clasificacion=id_clas,
        clasificacion=row.get("clasificacion") or (CLASIFICACION_MAP.get(id_clas) if id_clas else None),
        etiquetas=row.get("etiquetas"),
        dominios=row.get("dominios"),
        avance=row.get("avance"),
        fecha_registro=row.get("fecha_registro"),
        fecha_modificacion_do=row.get("fecha_modificacion_do"),
        fecha_modificacion_ds=row.get("fecha_modificacion_ds"),
        sn_activo=bool(row.get("sn_activo", True)),
    )


def _build_tablas_where(plataforma, servidor, base, esquema, clasificacion, tabla, owner_q, owner_type):
    conditions = ["f.sn_activo = 1"]
    params: list = []

    if plataforma:
        conditions.append("UPPER(IFNULL(f.txt_fuente_aprovisionamiento,'')) = UPPER(%s)")
        params.append(plataforma)
    if servidor:
        conditions.append("UPPER(IFNULL(f.txt_servidor,'')) LIKE UPPER(%s)")
        params.append(f"%{servidor}%")
    if base:
        conditions.append("UPPER(IFNULL(f.txt_host,'')) LIKE UPPER(%s)")
        params.append(f"%{base}%")
    if esquema:
        conditions.append("UPPER(IFNULL(f.txt_fuente_esquema,'')) LIKE UPPER(%s)")
        params.append(f"%{esquema}%")
    if tabla:
        conditions.append("UPPER(IFNULL(t.txt_desc_tabla,'')) LIKE UPPER(%s)")
        params.append(f"%{tabla}%")
    if clasificacion:
        rev = {"OFICIAL": 1, "TRABAJO": 2, "TEMPORAL": 3, "DESUSO": 4}
        cid = rev.get(clasificacion.upper())
        if cid:
            conditions.append("t.id_clasificacion = %s")
            params.append(cid)
        else:
            conditions.append("UPPER(IFNULL(c.clasificacion,'')) = UPPER(%s)")
            params.append(clasificacion)
    if owner_q:
        if owner_type == "steward":
            conditions.append(
                "(UPPER(IFNULL(t.data_steward,'')) LIKE UPPER(%s) OR UPPER(IFNULL(t.nombre_data_steward,'')) LIKE UPPER(%s))"
            )
            params += [f"%{owner_q}%", f"%{owner_q}%"]
        else:
            conditions.append(
                "(UPPER(IFNULL(t.data_owner,'')) LIKE UPPER(%s) OR UPPER(IFNULL(t.nombre_data_owner,'')) LIKE UPPER(%s))"
            )
            params += [f"%{owner_q}%", f"%{owner_q}%"]

    return " AND ".join(conditions), params


def _get_all_tablas_raw(conn) -> list[dict]:
    """Carga todas las tablas sin paginación y las guarda en caché TTL."""
    cache = get_tablas_all_cache()
    lock  = get_tablas_all_lock()

    with lock:
        cached = cache.get("all")
        if cached is not None:
            return cached

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                   t.id_fuente_aprovisionamiento AS id,
                   t.id_fuente_aprovisionamiento,
                   t.txt_desc_tabla,
                   f.txt_fuente_aprovisionamiento AS fuente,
                   f.txt_fuente_aprovisionamiento AS plataforma,
                   f.txt_servidor AS servidor,
                   f.txt_host AS `base`,
                   f.txt_fuente_esquema AS esquema,
                   t.txt_desc_tabla AS tabla,
                   t.descripcion_tabla, t.data_owner, t.nombre_data_owner,
                   t.data_steward, t.nombre_data_steward,
                   t.id_clasificacion, c.clasificacion, t.etiquetas,
                   t.avance, t.fecha_registro,
                   t.fecha_modificacion_do, t.fecha_modificacion_ds, f.sn_activo
            FROM t_tablas_oficiales t
            JOIN t_fuente_aprovisionamiento f
              ON f.id_fuente_aprovisionamiento = t.id_fuente_aprovisionamiento
            LEFT JOIN t_clasificacion_tablas c
              ON c.id_clasificacion = t.id_clasificacion
            WHERE f.sn_activo = 1
            ORDER BY f.txt_servidor, f.txt_host, f.txt_fuente_esquema, t.txt_desc_tabla
            """
        )
        rows = list(cursor.fetchall())

    with lock:
        cache["all"] = rows
    return rows


def _filter_tablas_raw(tablas, plataforma, servidor, base, esquema,
                       clasificacion, tabla, owner_q, owner_type) -> list[dict]:
    """Filtra la lista de tablas en memoria (equivalente a WHERE del SQL)."""
    result = []
    for t in tablas:
        if plataforma and (t.get("plataforma") or "").upper() != plataforma.upper():
            continue
        if servidor and servidor.upper() not in (t.get("servidor") or "").upper():
            continue
        if base and base.upper() not in (t.get("base") or "").upper():
            continue
        if esquema and esquema.upper() not in (t.get("esquema") or "").upper():
            continue
        if tabla and tabla.upper() not in (t.get("tabla") or "").upper():
            continue
        if clasificacion:
            rev = {"OFICIAL": 1, "TRABAJO": 2, "TEMPORAL": 3, "DESUSO": 4}
            cid = rev.get(clasificacion.upper())
            if cid:
                if t.get("id_clasificacion") != cid:
                    continue
            else:
                if (t.get("clasificacion") or "").upper() != clasificacion.upper():
                    continue
        if owner_q:
            field = "nombre_data_steward" if owner_type == "steward" else "nombre_data_owner"
            if owner_q.upper() not in (t.get(field) or "").upper():
                continue
        result.append(t)
    return result


def get_all_tablas(conn) -> list[TablaOficial]:
    """Retorna todas las tablas sin paginación (desde caché)."""
    return [_row_to_tabla(r) for r in _get_all_tablas_raw(conn)]


def get_tablas(conn, page=1, page_size=20, plataforma=None, servidor=None,
               base=None, esquema=None, clasificacion=None, tabla=None,
               owner_q=None, owner_type=None) -> PaginatedResponse[TablaOficial]:
    all_tablas = _get_all_tablas_raw(conn)
    filtered   = _filter_tablas_raw(
        all_tablas, plataforma, servidor, base, esquema,
        clasificacion, tabla, owner_q, owner_type,
    )
    total     = len(filtered)
    offset    = (page - 1) * page_size
    page_data = filtered[offset:offset + page_size]
    return PaginatedResponse.build(
        data=[_row_to_tabla(r) for r in page_data], total=total, page=page, page_size=page_size
    )


def get_tabla_by_id(conn, tabla_id: int) -> TablaOficial:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                   t.id_fuente_aprovisionamiento AS id,
                   t.id_fuente_aprovisionamiento,
                   t.txt_desc_tabla,
                   f.txt_fuente_aprovisionamiento AS fuente,
                   f.txt_fuente_aprovisionamiento AS plataforma,
                   f.txt_servidor AS servidor,
                   f.txt_host AS `base`,
                   f.txt_fuente_esquema AS esquema,
                   t.txt_desc_tabla AS tabla,
                   descripcion_tabla, data_owner, nombre_data_owner,
                   data_steward, nombre_data_steward,
                   t.id_clasificacion, c.clasificacion, etiquetas,
                   (
                       SELECT GROUP_CONCAT(DISTINCT d.descripcion_dominio ORDER BY d.descripcion_dominio SEPARATOR '; ')
                       FROM t_dominios_tablas_oficiales dto
                       JOIN t_mapa_dominios d ON d.id_dominio = dto.id_dominio_asociado
                       WHERE dto.id_fuente_aprovisionamiento = t.id_fuente_aprovisionamiento
                         AND dto.txt_desc_tabla = t.txt_desc_tabla
                   ) AS dominios,
                   t.avance, t.fecha_registro,
                   fecha_modificacion_do, fecha_modificacion_ds, f.sn_activo
            FROM t_tablas_oficiales t
            JOIN t_fuente_aprovisionamiento f
              ON f.id_fuente_aprovisionamiento = t.id_fuente_aprovisionamiento
            LEFT JOIN t_clasificacion_tablas c
              ON c.id_clasificacion = t.id_clasificacion
            WHERE t.id_fuente_aprovisionamiento = %s
            ORDER BY t.txt_desc_tabla
            LIMIT 1
            """,
            [tabla_id],
        )
        row = cursor.fetchone()
    if not row:
        raise NotFoundException(f"Tabla id={tabla_id} no encontrada")
    return _row_to_tabla(row)


def get_campos(conn, page=1, page_size=20, tabla_id=None, buscar=None,
               plataforma=None, servidor=None, base=None, esquema=None, tabla=None
               ) -> PaginatedResponse[Campo]:
    conditions = ["v.sn_activo = 1", "TRIM(IFNULL(v.desc_tecnica_atributo,'')) != ''"]
    params: list = []

    if tabla_id:
        conditions.append("v.id_fuente_aprovisionamiento = %s")
        params.append(tabla_id)
    if buscar:
        b = f"%{buscar}%"
        conditions.append(
            "(UPPER(v.desc_tecnica_atributo) LIKE UPPER(%s) "
            "OR UPPER(IFNULL(v.detalle_campo,'')) LIKE UPPER(%s) "
            "OR UPPER(IFNULL(v.txt_desc_atributo,'')) LIKE UPPER(%s))"
        )
        params += [b, b, b]
    if plataforma:
        conditions.append("UPPER(IFNULL(f.txt_fuente_aprovisionamiento,'')) = UPPER(%s)")
        params.append(plataforma)
    if servidor:
        conditions.append("UPPER(IFNULL(f.txt_servidor,'')) LIKE UPPER(%s)")
        params.append(f"%{servidor}%")
    if base:
        conditions.append("UPPER(IFNULL(f.txt_host,'')) LIKE UPPER(%s)")
        params.append(f"%{base}%")
    if esquema:
        conditions.append("UPPER(IFNULL(f.txt_fuente_esquema,'')) LIKE UPPER(%s)")
        params.append(f"%{esquema}%")
    if tabla:
        conditions.append("UPPER(IFNULL(v.desc_tecnica_tabla,'')) LIKE UPPER(%s)")
        params.append(f"%{tabla}%")

    where  = " AND ".join(conditions)
    offset = (page - 1) * page_size

    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT COUNT(1) AS total
            FROM t_atributos_inf_tecnica_larga v
            LEFT JOIN t_fuente_aprovisionamiento f ON f.id_fuente_aprovisionamiento = v.id_fuente_aprovisionamiento
            WHERE {where}
            """,
            params,
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            f"""
            SELECT
                v.desc_tecnica_atributo                         AS campo,
                CAST(IFNULL(v.id_atributos, '') AS CHAR)        AS codigo,
                IFNULL(v.txt_desc_atributo, '')                 AS atributo,
                IFNULL(v.detalle_campo, '')                     AS definicion,
                CAST(v.id_tipo_dato_atributo AS CHAR)           AS tipo,
                v.largo_atributo                                AS largo,
                CASE
                    WHEN v.largo_atributo REGEXP '^[0-9]+$'
                    THEN CAST(v.largo_atributo AS UNSIGNED)
                    ELSE NULL
                END                                             AS longitud,
                IFNULL(v.sn_nulo, '')                           AS permite_null,
                IFNULL(v.ordinal_position, 0)                   AS ordinal_position,
                CAST(IFNULL(v.golden_record_campo, 0) AS CHAR)  AS golden_record,
                v.desc_tecnica_tabla                            AS tabla,
                v.id_fuente_aprovisionamiento                   AS id_fuente,
                v.id_fuente_aprovisionamiento                   AS id_fuente_aprovisionamiento,
                f.txt_fuente_aprovisionamiento                  AS plataforma,
                f.txt_servidor                                  AS servidor,
                f.txt_host                                      AS `base`,
                f.txt_fuente_esquema                            AS esquema,
                IFNULL(t.descripcion_tabla, '')                 AS descripcion_tabla,
                CAST(IFNULL(t.avance, 0) AS CHAR)              AS avance,
                IFNULL(c.clasificacion, '')                     AS clasificacion,
                IFNULL(t.nombre_data_owner, '')                 AS nombre_data_owner,
                IFNULL(t.nombre_data_steward, '')               AS nombre_data_steward,
                v.usuario_modificacion_detalle                  AS usuario_modificacion,
                v.fecha_modificacion_detalle                    AS fecha_modificacion
            FROM t_atributos_inf_tecnica_larga v
            LEFT JOIN t_fuente_aprovisionamiento f
                ON f.id_fuente_aprovisionamiento = v.id_fuente_aprovisionamiento
            LEFT JOIN t_tablas_oficiales t
                ON t.id_fuente_aprovisionamiento = v.id_fuente_aprovisionamiento
                AND UPPER(TRIM(t.txt_desc_tabla)) = UPPER(TRIM(v.desc_tecnica_tabla))
            LEFT JOIN t_clasificacion_tablas c
                ON c.id_clasificacion = t.id_clasificacion
            WHERE {where}
            ORDER BY v.desc_tecnica_tabla, v.ordinal_position, v.desc_tecnica_atributo
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset],
        )
        rows = cursor.fetchall()

    data = []
    for r in rows:
        sv  = (r.get("servidor") or "").upper().strip()
        es  = (r.get("esquema")  or "").upper().strip()
        ba  = (r.get("base")     or "").upper().strip()
        tb  = (r.get("tabla")    or "").upper().strip()
        ca  = (r.get("campo")    or "").upper().strip()
        lt  = f"{sv}_{es}_{ba}_{tb}"
        data.append(Campo(
            llave_tabla=lt,
            llave_unica=f"{lt}_{ca}",
            campo=r.get("campo"),
            codigo=str(r.get("codigo") or ""),
            atributo=r.get("atributo") or "",
            definicion=r.get("definicion") or "",
            tipo=r.get("tipo") or "",
            largo=str(r.get("largo") or "-"),
            longitud=r.get("longitud"),
            permite_null=str(r.get("permite_null") or "-"),
            ordinal_position=r.get("ordinal_position"),
            golden_record=str(r.get("golden_record") or "0"),
            descripcion_tabla=r.get("descripcion_tabla") or "",
            avance=str(r.get("avance") or "0"),
            clasificacion=r.get("clasificacion") or "",
            nombre_data_owner=r.get("nombre_data_owner") or "",
            nombre_data_steward=r.get("nombre_data_steward") or "",
            plataforma=r.get("plataforma"),
            servidor=r.get("servidor"),
            base=r.get("base"),
            esquema=r.get("esquema"),
            tabla=r.get("tabla"),
            id_fuente=r.get("id_fuente"),
            id_fuente_aprovisionamiento=r.get("id_fuente_aprovisionamiento"),
            usuario_modificacion=r.get("usuario_modificacion"),
            fecha_modificacion=r.get("fecha_modificacion"),
        ))
    return PaginatedResponse.build(data=data, total=total, page=page, page_size=page_size)


def get_arbol(conn) -> ArbolMetadatos:
    cache = get_arbol_cache()
    lock  = get_arbol_lock()

    with lock:
        cached = cache.get("arbol")
        if cached:
            return cached

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT
                IFNULL(f.txt_servidor, 'SIN_SERVIDOR')       AS servidor,
                IFNULL(f.txt_host,   'SIN_BASE')             AS base,
                IFNULL(f.txt_fuente_esquema,  'SIN_ESQUEMA') AS esquema,
                t.txt_desc_tabla AS tabla
            FROM t_tablas_oficiales t
            JOIN t_fuente_aprovisionamiento f
                ON f.id_fuente_aprovisionamiento = t.id_fuente_aprovisionamiento
            WHERE f.sn_activo = 1
            ORDER BY servidor, `base`, esquema, tabla
            """
        )
        rows = cursor.fetchall()

    tree: dict = {}
    for r in rows:
        srv, base, esq, tbl = r["servidor"], r["base"], r["esquema"], r["tabla"]
        tree.setdefault(srv, {}).setdefault(base, {}).setdefault(esq, []).append(tbl)

    servidores = [
        NodoServidor(nombre=srv, bases=[
            NodoBase(nombre=base, esquemas=[
                NodoEsquema(nombre=esq, tablas=tablas)
                for esq, tablas in esqs.items()
            ])
            for base, esqs in bases.items()
        ])
        for srv, bases in tree.items()
    ]

    arbol = ArbolMetadatos(servidores=servidores, cached_at=datetime.now().isoformat())
    with lock:
        cache["arbol"] = arbol
    return arbol


def get_owners_facets(conn, tipo: str | None = None) -> list[str]:
    with conn.cursor() as cursor:
        if tipo == "steward":
            cursor.execute(
                "SELECT DISTINCT TRIM(data_steward) AS v FROM t_tablas_oficiales WHERE data_steward IS NOT NULL ORDER BY v"
            )
        else:
            cursor.execute(
                "SELECT DISTINCT TRIM(data_owner) AS v FROM t_tablas_oficiales WHERE data_owner IS NOT NULL ORDER BY v"
            )
        return [r["v"] for r in cursor.fetchall() if r["v"]]


def get_recomendaciones(conn, tabla_id: int) -> list[RecomendacionDoc]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT v.desc_tecnica_atributo AS campo
            FROM t_atributos_inf_tecnica_larga v
            WHERE v.id_fuente_aprovisionamiento = %s
              AND (v.detalle_campo IS NULL OR TRIM(v.detalle_campo) = '')
            ORDER BY v.desc_tecnica_atributo
            """,
            [tabla_id],
        )
        rows = cursor.fetchall()

    result = []
    for r in rows:
        campo = r.get("campo") or ""
        campo_lower = campo.lower()
        for prefijo, plantilla in PREFIJOS_SUGERENCIA.items():
            if campo_lower.startswith(prefijo):
                entidad = campo_lower[len(prefijo):].replace("_", " ")
                sugerencia = re.sub(r"\{[\w]+\}", entidad, plantilla)
                result.append(RecomendacionDoc(campo=campo, sugerencia=sugerencia, prefijo_detectado=prefijo))
                break
    return result


def update_tabla(conn, tabla_id: int, data: TablaUpdate,
                 usuario_email: str, usuario_codigo: str | None) -> TablaOficial:
    tabla_actual = get_tabla_by_id(conn, tabla_id)
    updates, params = [], []
    usuario = usuario_codigo or usuario_email

    if data.descripcion_tabla is not None:
        updates.append("descripcion_tabla = %s")
        params.append(data.descripcion_tabla)
    if data.data_owner is not None:
        updates += ["data_owner = %s", "usuario_modificacion_do = %s", "fecha_modificacion_do = NOW()"]
        params += [data.data_owner, usuario]
    if data.nombre_data_owner is not None:
        updates.append("nombre_data_owner = %s")
        params.append(data.nombre_data_owner)
    if data.data_steward is not None:
        updates += ["data_steward = %s", "usuario_modificacion_ds = %s", "fecha_modificacion_ds = NOW()"]
        params += [data.data_steward, usuario]
    if data.nombre_data_steward is not None:
        updates.append("nombre_data_steward = %s")
        params.append(data.nombre_data_steward)
    if data.id_clasificacion is not None:
        updates.append("id_clasificacion = %s")
        params.append(data.id_clasificacion)
    if data.etiquetas is not None:
        updates += ["etiquetas = %s", "usuario_modificacion_etiqueta = %s"]
        params += [data.etiquetas, usuario]

    if updates:
        params.append(tabla_id)
        with conn.cursor() as cursor:
            cursor.execute(
                f"UPDATE t_tablas_oficiales SET {', '.join(updates)} WHERE id_fuente_aprovisionamiento = %s", params
            )
        invalidar_arbol_cache()
        invalidar_tablas_all_cache()

    if data.dominios_ids is not None:
        txt_tabla = tabla_actual.txt_desc_tabla or ""
        with conn.cursor() as cursor:
            for id_dominio in data.dominios_ids:
                cursor.execute(
                    "INSERT IGNORE INTO t_dominios_tablas_oficiales"
                    " (id_fuente_aprovisionamiento, txt_desc_tabla, id_dominio_asociado)"
                    " VALUES (%s, %s, %s)",
                    [tabla_id, txt_tabla, id_dominio],
                )

    return get_tabla_by_id(conn, tabla_id)


def get_dominios_tabla(conn, tabla_id: int) -> list[dict]:
    """Retorna los dominios asociados a una tabla como [{id_dominio, descripcion_dominio}]."""
    tabla = get_tabla_by_id(conn, tabla_id)
    txt_tabla = tabla.txt_desc_tabla or ""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT d.id_dominio, d.descripcion_dominio
            FROM t_dominios_tablas_oficiales dto
            JOIN t_mapa_dominios d ON d.id_dominio = dto.id_dominio_asociado
            WHERE dto.id_fuente_aprovisionamiento = %s
              AND dto.txt_desc_tabla = %s
            ORDER BY d.descripcion_dominio
            """,
            [tabla_id, txt_tabla],
        )
        return [{"id_dominio": r["id_dominio"], "descripcion_dominio": r["descripcion_dominio"]}
                for r in cursor.fetchall()]


def update_campo(conn, tabla_id: int, campo_nombre: str,
                 data: CampoUpdate, usuario: str) -> dict:
    updates, params = [], []
    detalle = data.detalle if data.detalle is not None else data.descripcion
    if detalle is not None:
        updates += ["detalle_campo = %s", "usuario_modificacion_detalle = %s", "fecha_modificacion_detalle = NOW()"]
        params += [detalle, usuario]

    if "id_atributos" in data.model_fields_set:
        updates.append("id_atributos = %s")
        params.append(data.id_atributos)  # None → NULL en MySQL (limpia el atributo)

    if not updates:
        return {"ok": True}

    params += [tabla_id, campo_nombre]
    with conn.cursor() as cursor:
        cursor.execute(
            f"UPDATE t_atributos_inf_tecnica_larga SET {', '.join(updates)} WHERE id_fuente_aprovisionamiento=%s AND desc_tecnica_atributo=%s",
            params,
        )
        return {"ok": True, "updated_rows": cursor.rowcount}


def get_empleados(conn) -> list[Empleado]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT CAST(codigo AS CHAR(50)) AS codigo,
                   TRIM(CONCAT(IFNULL(nombres,''), ' ', IFNULL(apellido_paterno,''), ' ', IFNULL(apellido_materno,''))) AS nombre_completo
            FROM Tmp_DATOS_EMPLEADOS
            WHERE estado = 'A'
            ORDER BY nombre_completo
            """
        )
        return [Empleado(codigo=r["codigo"], nombre_completo=r["nombre_completo"])
                for r in cursor.fetchall()]


def get_filtros(conn) -> FiltrosMetadatos:
    all_tablas  = _get_all_tablas_raw(conn)
    servidores  = sorted({t.get("servidor") for t in all_tablas if t.get("servidor")})
    plataformas = sorted({t.get("plataforma") for t in all_tablas if t.get("plataforma")})
    clases_map  = {}
    for t in all_tablas:
        cid  = t.get("id_clasificacion")
        clas = t.get("clasificacion")
        if cid and clas:
            clases_map[cid] = clas
    clasificaciones = [{"id": k, "descripcion": v} for k, v in sorted(clases_map.items())]
    return FiltrosMetadatos(servidores=servidores, plataformas=plataformas, clasificaciones=clasificaciones)
