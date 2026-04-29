import logging
from app.models.aprobaciones import (
    Aprobacion, AprobacionCreate, AprobacionAprobarBody, AprobacionRechazarBody,
)
from app.models.metadatos import TablaUpdate
from app.models.common import PaginatedResponse
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)

CLASIFICACION_A_ID = {"OFICIAL": 1, "TRABAJO": 2, "TEMPORAL": 3, "DESUSO": 4}


def _row_to_aprobacion(row: dict) -> Aprobacion:
    return Aprobacion(
        id=row.get("id") or 0,
        tipo_cambio=row.get("TIPO_CAMBIO") or row.get("tipo_cambio") or 0,
        estado=row.get("ESTADO_APROBACION") or row.get("estado_aprobacion") or "PENDIENTE",
        original=row.get("ORIGINAL") or row.get("original"),
        solicitado=row.get("SOLICITADO") or row.get("solicitado"),
        autor_solicitud=row.get("AUTOR_SOLICITUD") or row.get("autor_solicitud"),
        nombre_autor=row.get("NOMBRE_AUTOR") or row.get("nombre_autor"),
        fecha_solicitud=row.get("FECHA_SOLICITUD") or row.get("fecha_solicitud"),
        fecha_resolucion=row.get("FECHA_RESOLUCION") or row.get("fecha_resolucion"),
        resolvio=row.get("RESOLVIO") or row.get("resolvio"),
        dato1=row.get("DATO1") or row.get("dato1"),
        dato2=row.get("DATO2") or row.get("dato2"),
        dato3=row.get("DATO3") or row.get("dato3"),
        dato4=row.get("DATO4") or row.get("dato4"),
        dato5=row.get("DATO5") or row.get("dato5"),
        dato6=row.get("DATO6") or row.get("dato6"),
        dato7=row.get("DATO7") or row.get("dato7"),
        dato8=row.get("DATO8") or row.get("dato8"),
        descripcion_cambio=row.get("DESCRIPCION_CAMBIO") or row.get("descripcion_cambio"),
    )


def get_aprobaciones(conn, estado=None, buscar=None, page=1, page_size=30
                     ) -> PaginatedResponse[Aprobacion]:
    conditions = ["1=1"]
    params: list = []

    if estado and estado != "TODOS":
        conditions.append("ESTADO_APROBACION = %s")
        params.append(estado)
    if buscar:
        t = f"%{buscar}%"
        conditions.append(
            "(UPPER(IFNULL(DATO2,'')) LIKE UPPER(%s) "
            "OR UPPER(IFNULL(ORIGINAL,'')) LIKE UPPER(%s) "
            "OR UPPER(IFNULL(SOLICITADO,'')) LIKE UPPER(%s) "
            "OR UPPER(IFNULL(AUTOR_SOLICITUD,'')) LIKE UPPER(%s) "
            "OR UPPER(IFNULL(DATO3,'')) LIKE UPPER(%s))"
        )
        params += [t, t, t, t, t]

    where = " AND ".join(conditions)
    offset = (page - 1) * page_size

    with conn.cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(1) AS total FROM t_aprobaciones WHERE {where}", params
        )
        total = cursor.fetchone()["total"]

        cursor.execute(
            f"""
            SELECT id, TIPO_CAMBIO, ESTADO_APROBACION, ORIGINAL, SOLICITADO,
                   AUTOR_SOLICITUD, NOMBRE_AUTOR, FECHA_SOLICITUD, FECHA_RESOLUCION,
                   RESOLVIO, DATO1, DATO2, DATO3, DATO4, DATO5, DATO6, DATO7, DATO8,
                   DESCRIPCION_CAMBIO
            FROM t_aprobaciones
            WHERE {where}
            ORDER BY FECHA_SOLICITUD DESC
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset],
        )
        rows = cursor.fetchall()

    return PaginatedResponse.build(
        data=[_row_to_aprobacion(r) for r in rows], total=total, page=page, page_size=page_size
    )


def get_aprobacion_by_id(conn, aprobacion_id: int) -> Aprobacion:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, TIPO_CAMBIO, ESTADO_APROBACION, ORIGINAL, SOLICITADO,
                   AUTOR_SOLICITUD, NOMBRE_AUTOR, FECHA_SOLICITUD, FECHA_RESOLUCION,
                   RESOLVIO, DATO1, DATO2, DATO3, DATO4, DATO5, DATO6, DATO7, DATO8,
                   DESCRIPCION_CAMBIO
            FROM t_aprobaciones WHERE id = %s
            """,
            [aprobacion_id],
        )
        row = cursor.fetchone()
    if not row:
        raise NotFoundException(f"Aprobacion id={aprobacion_id} no encontrada")
    return _row_to_aprobacion(row)


def crear_aprobacion(conn, data: AprobacionCreate, autor_email: str, autor_nombre: str) -> Aprobacion:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO t_aprobaciones
                (TIPO_CAMBIO, ORIGINAL, SOLICITADO, AUTOR_SOLICITUD, NOMBRE_AUTOR,
                 FECHA_SOLICITUD, ESTADO_APROBACION,
                 DATO1, DATO2, DATO3, DATO4, DATO5, DATO6, DATO7, DESCRIPCION_CAMBIO)
            VALUES (%s,%s,%s,%s,%s,NOW(),'PENDIENTE',%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            [data.tipo_cambio, data.original, data.solicitado, autor_email, autor_nombre,
             data.dato1, data.dato2, data.dato3, data.dato4,
             data.dato5, data.dato6, data.dato7, data.descripcion_cambio],
        )
        new_id = cursor.lastrowid
    return get_aprobacion_by_id(conn, new_id)


def _aplicar_cambio(conn, aprobacion: Aprobacion, autor_codigo: str) -> None:
    with conn.cursor() as cursor:
        tc = aprobacion.tipo_cambio

        if tc == 1:
            cursor.execute(
                "UPDATE t_tablas_oficiales SET data_owner=%s, nombre_data_owner=%s, usuario_modificacion_do=%s, fecha_modificacion_do=NOW() WHERE id=%s",
                [aprobacion.solicitado, aprobacion.dato2, autor_codigo, aprobacion.dato1],
            )
        elif tc == 2:
            cursor.execute(
                "UPDATE t_tablas_oficiales SET data_steward=%s, nombre_data_steward=%s, usuario_modificacion_ds=%s, fecha_modificacion_ds=NOW() WHERE id=%s",
                [aprobacion.solicitado, aprobacion.dato2, autor_codigo, aprobacion.dato1],
            )
        elif tc == 3:
            clas_id = CLASIFICACION_A_ID.get((aprobacion.solicitado or "").upper())
            if clas_id:
                cursor.execute(
                    "UPDATE t_tablas_oficiales SET id_clasificacion=%s WHERE id=%s",
                    [clas_id, aprobacion.dato1],
                )
        elif tc == 4:
            ids_str = aprobacion.solicitado or ""
            for id_str in ids_str.split(";"):
                id_str = id_str.strip()
                if not id_str:
                    continue
                try:
                    id_dominio = int(id_str)
                except ValueError:
                    continue
                # INSERT IGNORE previene duplicados via UNIQUE KEY
                cursor.execute(
                    "INSERT IGNORE INTO t_dominios_tablas_oficiales (id_fuente, txt_tabla, id_dominio) VALUES (%s,%s,%s)",
                    [aprobacion.dato1, aprobacion.dato2, id_dominio],
                )
        elif tc == 5:
            cursor.execute(
                "UPDATE t_tablas_oficiales SET descripcion_tabla=%s WHERE id=%s",
                [aprobacion.solicitado, aprobacion.dato1],
            )
        elif tc == 9:
            cursor.execute(
                "UPDATE t_tablas_oficiales SET etiquetas=%s, usuario_modificacion_etiqueta=%s WHERE id=%s",
                [aprobacion.solicitado, autor_codigo, aprobacion.dato1],
            )


def aprobar_aprobacion(conn, aprobacion_id: int, body: AprobacionAprobarBody,
                       autor_email: str, autor_codigo: str) -> Aprobacion:
    aprobacion = get_aprobacion_by_id(conn, aprobacion_id)
    try:
        _aplicar_cambio(conn, aprobacion, autor_codigo)
    except Exception as e:
        logger.error("Error aplicando cambio tipo=%d id=%d: %s", aprobacion.tipo_cambio, aprobacion_id, e)

    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE t_aprobaciones SET ESTADO_APROBACION='APROBADO', FECHA_RESOLUCION=NOW(), RESOLVIO=%s WHERE id=%s",
            [autor_email, aprobacion_id],
        )
    _registrar_auditoria(conn, aprobacion, "APROBADO", autor_email, autor_codigo, body.comentario)
    return get_aprobacion_by_id(conn, aprobacion_id)


def rechazar_aprobacion(conn, aprobacion_id: int, body: AprobacionRechazarBody,
                        autor_email: str) -> Aprobacion:
    get_aprobacion_by_id(conn, aprobacion_id)
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE t_aprobaciones SET ESTADO_APROBACION='RECHAZADO', FECHA_RESOLUCION=NOW(), RESOLVIO=%s, DATO8=%s WHERE id=%s",
            [autor_email, body.motivo, aprobacion_id],
        )
    ap = get_aprobacion_by_id(conn, aprobacion_id)
    _registrar_auditoria(conn, ap, "RECHAZADO", autor_email, None, body.motivo)
    return ap


def _registrar_auditoria(conn, aprobacion: Aprobacion, accion: str,
                         usuario_email: str, usuario_codigo: str | None, detalle: str | None) -> None:
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO t_auditoria_cambios
                    (tabla_afectada, operacion, registro_id, campo_modificado,
                     valor_anterior, valor_nuevo, usuario_email, usuario_codigo,
                     modulo, id_aprobacion, detalle_json)
                VALUES ('t_aprobaciones',%s,%s,%s,%s,%s,%s,%s,'aprobaciones',%s,%s)
                """,
                [accion, str(aprobacion.id), f"tipo_cambio={aprobacion.tipo_cambio}",
                 aprobacion.original, aprobacion.solicitado,
                 usuario_email, usuario_codigo, aprobacion.id, detalle],
            )
    except Exception as e:
        logger.warning("No se pudo registrar auditoria: %s", e)


def crear_desde_tabla_update(conn, tabla_id: int, data: TablaUpdate,
                             autor_email: str, autor_codigo: str) -> list[Aprobacion]:
    creadas = []
    if data.data_owner is not None:
        creadas.append(crear_aprobacion(conn, AprobacionCreate(
            tipo_cambio=1, solicitado=data.data_owner,
            dato1=str(tabla_id), dato2=data.nombre_data_owner,
            descripcion_cambio="Solicitud de cambio de Data Owner",
        ), autor_email, autor_codigo))

    if data.data_steward is not None:
        creadas.append(crear_aprobacion(conn, AprobacionCreate(
            tipo_cambio=2, solicitado=data.data_steward,
            dato1=str(tabla_id), dato2=data.nombre_data_steward,
            descripcion_cambio="Solicitud de cambio de Data Steward",
        ), autor_email, autor_codigo))

    if data.id_clasificacion is not None:
        rev = {1: "OFICIAL", 2: "TRABAJO", 3: "TEMPORAL", 4: "DESUSO"}
        creadas.append(crear_aprobacion(conn, AprobacionCreate(
            tipo_cambio=3, solicitado=rev.get(data.id_clasificacion, str(data.id_clasificacion)),
            dato1=str(tabla_id), descripcion_cambio="Solicitud de cambio de Clasificacion",
        ), autor_email, autor_codigo))

    if data.descripcion_tabla is not None:
        creadas.append(crear_aprobacion(conn, AprobacionCreate(
            tipo_cambio=5, solicitado=data.descripcion_tabla,
            dato1=str(tabla_id), descripcion_cambio="Solicitud de cambio de Descripcion",
        ), autor_email, autor_codigo))

    if data.etiquetas is not None:
        creadas.append(crear_aprobacion(conn, AprobacionCreate(
            tipo_cambio=9, solicitado=data.etiquetas,
            dato1=str(tabla_id), descripcion_cambio="Solicitud de cambio de Medallon",
        ), autor_email, autor_codigo))

    return creadas
