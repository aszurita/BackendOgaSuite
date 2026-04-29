import logging
import re
from datetime import datetime
from app.models.metadatos import (
    TablaOficial, TablaUpdate, Campo, CampoUpdate,
    RecomendacionDoc, ArbolMetadatos, NodoServidor, NodoBase, NodoEsquema,
    Empleado, FiltrosMetadatos,
)
from app.models.common import PaginatedResponse
from app.core.cache import get_arbol_cache, get_arbol_lock, invalidar_arbol_cache
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
        clasificacion=CLASIFICACION_MAP.get(id_clas) if id_clas else None,
        etiquetas=row.get("etiquetas"),
        dominios=row.get("dominios"),
        fecha_modificacion_do=row.get("fecha_modificacion_do"),
        fecha_modificacion_ds=row.get("fecha_modificacion_ds"),
        sn_activo=bool(row.get("sn_activo", True)),
    )


def _build_tablas_where(plataforma, servidor, base, esquema, clasificacion, tabla, owner_q, owner_type):
    conditions = ["t.sn_activo = 1"]
    params: list = []

    if plataforma:
        conditions.append("UPPER(t.plataforma) = UPPER(%s)")
        params.append(plataforma)
    if servidor:
        conditions.append("UPPER(t.servidor) LIKE UPPER(%s)")
        params.append(f"%{servidor}%")
    if base:
        conditions.append("UPPER(t.`base`) LIKE UPPER(%s)")
        params.append(f"%{base}%")
    if esquema:
        conditions.append("UPPER(t.esquema) LIKE UPPER(%s)")
        params.append(f"%{esquema}%")
    if tabla:
        conditions.append("UPPER(t.tabla) LIKE UPPER(%s)")
        params.append(f"%{tabla}%")
    if clasificacion:
        rev = {"OFICIAL": 1, "TRABAJO": 2, "TEMPORAL": 3, "DESUSO": 4}
        cid = rev.get(clasificacion.upper())
        if cid:
            conditions.append("t.id_clasificacion = %s")
            params.append(cid)
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


def get_tablas(conn, page=1, page_size=20, plataforma=None, servidor=None,
               base=None, esquema=None, clasificacion=None, tabla=None,
               owner_q=None, owner_type=None) -> PaginatedResponse[TablaOficial]:
    where, params = _build_tablas_where(plataforma, servidor, base, esquema, clasificacion, tabla, owner_q, owner_type)
    offset = (page - 1) * page_size

    with conn.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(1) AS total FROM t_tablas_oficiales t WHERE {where}", params)
        total = cursor.fetchone()["total"]

        cursor.execute(
            f"""
            SELECT t.id, t.plataforma, t.servidor, t.`base`, t.esquema, t.tabla,
                   t.descripcion_tabla, t.data_owner, t.nombre_data_owner,
                   t.data_steward, t.nombre_data_steward,
                   t.id_clasificacion, t.etiquetas, t.dominios,
                   t.fecha_modificacion_do, t.fecha_modificacion_ds, t.sn_activo
            FROM t_tablas_oficiales t
            WHERE {where}
            ORDER BY t.servidor, t.`base`, t.esquema, t.tabla
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset],
        )
        rows = cursor.fetchall()

    return PaginatedResponse.build(
        data=[_row_to_tabla(r) for r in rows], total=total, page=page, page_size=page_size
    )


def get_tabla_by_id(conn, tabla_id: int) -> TablaOficial:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, plataforma, servidor, `base`, esquema, tabla,
                   descripcion_tabla, data_owner, nombre_data_owner,
                   data_steward, nombre_data_steward,
                   id_clasificacion, etiquetas, dominios,
                   fecha_modificacion_do, fecha_modificacion_ds, sn_activo
            FROM t_tablas_oficiales WHERE id = %s
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
    conditions = ["TRIM(IFNULL(v.desc_tecnica_atributo,'')) != ''"]
    params: list = []

    if tabla_id:
        conditions.append("v.id_fuente_aprovisionamiento = %s")
        params.append(tabla_id)
    if buscar:
        t = f"%{buscar}%"
        conditions.append(
            "(UPPER(v.desc_tecnica_atributo) LIKE UPPER(%s) "
            "OR UPPER(IFNULL(v.txt_desc_atributo,'')) LIKE UPPER(%s) "
            "OR UPPER(IFNULL(v.detalle_campo,'')) LIKE UPPER(%s))"
        )
        params += [t, t, t]
    if plataforma:
        conditions.append("UPPER(IFNULL(f.plataforma,'')) = UPPER(%s)")
        params.append(plataforma)
    if servidor:
        conditions.append("UPPER(IFNULL(f.servidor,'')) LIKE UPPER(%s)")
        params.append(f"%{servidor}%")
    if base:
        conditions.append("UPPER(IFNULL(f.`base`,'')) LIKE UPPER(%s)")
        params.append(f"%{base}%")
    if esquema:
        conditions.append("UPPER(IFNULL(f.esquema,'')) LIKE UPPER(%s)")
        params.append(f"%{esquema}%")
    if tabla:
        conditions.append("UPPER(IFNULL(v.desc_tecnica_tabla,'')) LIKE UPPER(%s)")
        params.append(f"%{tabla}%")

    where = " AND ".join(conditions)
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
            SELECT v.desc_tecnica_atributo AS campo,
                   v.txt_desc_atributo     AS descripcion,
                   v.detalle_campo         AS detalle,
                   v.tipo_dato, v.longitud,
                   v.desc_tecnica_tabla    AS tabla,
                   v.id_fuente_aprovisionamiento AS id_fuente,
                   f.plataforma, f.servidor, f.`base`, f.esquema,
                   v.usuario_modificacion_detalle AS usuario_modificacion,
                   v.fecha_modificacion_detalle   AS fecha_modificacion
            FROM t_atributos_inf_tecnica_larga v
            LEFT JOIN t_fuente_aprovisionamiento f ON f.id_fuente_aprovisionamiento = v.id_fuente_aprovisionamiento
            WHERE {where}
            ORDER BY v.desc_tecnica_tabla, v.desc_tecnica_atributo
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset],
        )
        rows = cursor.fetchall()

    data = []
    for r in rows:
        llave = f"{r.get('servidor') or ''}_{r.get('esquema') or ''}_{r.get('base') or ''}_{r.get('tabla') or ''}"
        data.append(Campo(
            llave_tabla=llave,
            campo=r.get("campo"),
            tipo_dato=r.get("tipo_dato"),
            longitud=r.get("longitud"),
            descripcion=r.get("descripcion"),
            detalle=r.get("detalle"),
            plataforma=r.get("plataforma"),
            servidor=r.get("servidor"),
            base=r.get("base"),
            esquema=r.get("esquema"),
            tabla=r.get("tabla"),
            id_fuente=r.get("id_fuente"),
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
                IFNULL(f.servidor, 'SIN_SERVIDOR') AS servidor,
                IFNULL(f.`base`,   'SIN_BASE')      AS base,
                IFNULL(f.esquema,  'SIN_ESQUEMA')   AS esquema,
                t.tabla
            FROM t_tablas_oficiales t
            JOIN t_fuente_aprovisionamiento f
                ON f.id_fuente_aprovisionamiento = t.id_fuente_aprovisionamiento
            WHERE t.sn_activo = 1
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
                "SELECT DISTINCT TRIM(data_steward) AS v FROM t_tablas_oficiales WHERE data_steward IS NOT NULL AND sn_activo=1 ORDER BY v"
            )
        else:
            cursor.execute(
                "SELECT DISTINCT TRIM(data_owner) AS v FROM t_tablas_oficiales WHERE data_owner IS NOT NULL AND sn_activo=1 ORDER BY v"
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
    get_tabla_by_id(conn, tabla_id)
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
    if data.dominios is not None:
        updates.append("dominios = %s")
        params.append(data.dominios)

    if not updates:
        return get_tabla_by_id(conn, tabla_id)

    params.append(tabla_id)
    with conn.cursor() as cursor:
        cursor.execute(
            f"UPDATE t_tablas_oficiales SET {', '.join(updates)} WHERE id = %s", params
        )
    invalidar_arbol_cache()
    return get_tabla_by_id(conn, tabla_id)


def update_campo(conn, tabla_id: int, campo_nombre: str,
                 data: CampoUpdate, usuario: str) -> dict:
    updates, params = [], []
    if data.detalle is not None:
        updates += ["detalle_campo = %s", "usuario_modificacion_detalle = %s", "fecha_modificacion_detalle = NOW()"]
        params += [data.detalle, usuario]
    if data.descripcion is not None:
        updates.append("txt_desc_atributo = %s")
        params.append(data.descripcion)

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
            SELECT CAST(CODIGO AS CHAR(50)) AS codigo,
                   TRIM(CONCAT(IFNULL(NOMBRES,''), ' ', IFNULL(APELLIDOS,''))) AS nombre_completo
            FROM Tmp_DATOS_EMPLEADOS
            WHERE estado = 'A'
            ORDER BY nombre_completo
            """
        )
        return [Empleado(codigo=r["codigo"], nombre_completo=r["nombre_completo"])
                for r in cursor.fetchall()]


def get_filtros(conn) -> FiltrosMetadatos:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT DISTINCT plataforma FROM t_tablas_oficiales WHERE plataforma IS NOT NULL ORDER BY plataforma"
        )
        plataformas = [r["plataforma"] for r in cursor.fetchall()]

        cursor.execute(
            "SELECT DISTINCT servidor FROM t_fuente_aprovisionamiento WHERE servidor IS NOT NULL ORDER BY servidor"
        )
        servidores = [r["servidor"] for r in cursor.fetchall()]

        cursor.execute(
            "SELECT id_clasificacion, descripcion FROM t_clasificacion_tablas ORDER BY id_clasificacion"
        )
        clasificaciones = [{"id": r["id_clasificacion"], "descripcion": r["descripcion"]}
                           for r in cursor.fetchall()]

    return FiltrosMetadatos(servidores=servidores, plataformas=plataformas, clasificaciones=clasificaciones)
