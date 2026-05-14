import logging

logger = logging.getLogger(__name__)


def get_ingenieros_calidad(conn) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT NOMBRE AS label, CODIGO_EMPLEADO AS value
            FROM Dw_dim_colaboradores
            WHERE PUESTO LIKE '%QUALITY AND COMPLIANCE%' AND ESTADO = 'A'
            ORDER BY NOMBRE
            LIMIT 50
            """
        )
        return [
            {"value": str(r.get("value") or ""), "label": str(r.get("label") or "")}
            for r in cursor.fetchall()
            if r.get("value")
        ]


def get_backlog_item(conn, servidor: str, base: str, esquema: str, tabla: str) -> dict | None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT ingeniero_asignado, ingeniero_calidad, promedio_buena_calidad,
                   estado, fec_creacion, fec_modificacion
            FROM T_Calidad_Backlog
            WHERE UPPER(SERVIDOR) = UPPER(%s) AND UPPER(BASE) = UPPER(%s)
              AND UPPER(ESQUEMA) = UPPER(%s) AND UPPER(TABLA) = UPPER(%s)
            LIMIT 1
            """,
            (servidor, base, esquema, tabla),
        )
        return cursor.fetchone()


def create_backlog_item(conn, data: dict) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO T_Calidad_Backlog
                (SERVIDOR, BASE, ESQUEMA, TABLA, INGENIERO_CALIDAD, INGENIERO_ASIGNADO,
                 ESTADO, OBSERVACION, FEC_CREACION, USUARIO_INGRESO,
                 FEC_MODIFICACION, USUARIO_MODIFICACION, PERIODICIDAD)
            VALUES (%s, %s, %s, %s, %s, %s, %s, '', %s, %s, NULL, '', NULL)
            """,
            (
                data["servidor"], data["base"], data["esquema"], data["tabla"],
                data["ingeniero_calidad"], data["ingeniero_asignado"],
                data.get("estado", "Pendiente"),
                data.get("fec_creacion"), data.get("usuario_ingreso", ""),
            ),
        )
    conn.commit()


def update_backlog_item(conn, data: dict) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE T_Calidad_Backlog
            SET INGENIERO_CALIDAD = %s, INGENIERO_ASIGNADO = %s,
                FEC_MODIFICACION = %s, USUARIO_MODIFICACION = %s
            WHERE UPPER(SERVIDOR) = UPPER(%s) AND UPPER(BASE) = UPPER(%s)
              AND UPPER(ESQUEMA) = UPPER(%s) AND UPPER(TABLA) = UPPER(%s)
            """,
            (
                data["ingeniero_calidad"], data["ingeniero_asignado"],
                data.get("fec_modificacion"), data.get("usuario_modificacion", ""),
                data["servidor"], data["base"], data["esquema"], data["tabla"],
            ),
        )
    conn.commit()


def get_web_user(conn, codigo: str) -> str | None:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT web_user FROM tmp_datos_empleados WHERE codigo = %s LIMIT 1",
            (codigo,),
        )
        row = cursor.fetchone()
        return str(row.get("web_user") or "") if row else None


def get_calidad_info_by_clave(conn, servidor: str, base: str, esquema: str, tabla: str) -> dict | None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT ingeniero_calidad, promedio_buena_calidad, estado,
                   fec_modificacion, fec_creacion
            FROM T_Calidad_Backlog
            WHERE UPPER(SERVIDOR) = UPPER(%s) AND UPPER(BASE) = UPPER(%s)
              AND UPPER(ESQUEMA) = UPPER(%s) AND UPPER(TABLA) = UPPER(%s)
            ORDER BY fec_modificacion DESC
            LIMIT 1
            """,
            (servidor, base, esquema, tabla),
        )
        row = cursor.fetchone()
    if not row:
        return None
    pct_raw = row.get("promedio_buena_calidad")
    pct_num = float(pct_raw) if pct_raw is not None else None
    if pct_num is None:
        return None
    fecha = str(row.get("fec_modificacion") or row.get("fec_creacion") or "").strip()
    return {
        "pct": pct_num,
        "ingeniero": str(row.get("ingeniero_calidad") or "").strip(),
        "fecha": fecha,
        "estado": str(row.get("estado") or "").strip(),
    }


def insert_cola_mensaje(conn, data: dict) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO t_cola_mensajes
                (NOMBRE_PERSONA, USUARIO_PERSONA, ASUNTO_CORREO, CUERPO_CORREO,
                 ENVIADO, FECHA_ENVIO, FECHA_INGRESO_EN_COLA, FIRMA)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                data.get("nombre_persona"), data.get("usuario_persona"),
                data.get("asunto_correo"), data.get("cuerpo_correo"),
                data.get("enviado", 0), data.get("fecha_envio"),
                data.get("fecha_ingreso_en_cola"), data.get("firma"),
            ),
        )
    conn.commit()
