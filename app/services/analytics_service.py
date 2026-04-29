import logging
from app.models.analytics import VisitaCreate, VisitaResumen
from app.models.auth import CurrentUser

logger = logging.getLogger(__name__)


def registrar_visita(conn, data: VisitaCreate, current_user: CurrentUser) -> None:
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO T_VISITAS_OGA_NEW
                    (USUARIO, CODIGO_EMPLEADO, DESC_PAGINA, SUB_PAGINA,
                     CENTRO_COSTO, DEPARTAMENTO, FECHA)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """,
                [
                    current_user.username,
                    current_user.codigo_empleado,
                    data.desc_pagina.upper(),
                    data.sub_pagina,
                    current_user.centro_costo,
                    current_user.departamento,
                ],
            )
    except Exception as e:
        logger.warning("No se pudo registrar visita para %s: %s", current_user.email, e)


def get_resumen_visitas(conn) -> list[VisitaResumen]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT DESC_PAGINA, COUNT(1) AS total, MAX(FECHA) AS ultimo_acceso
            FROM T_VISITAS_OGA_NEW
            GROUP BY DESC_PAGINA
            ORDER BY total DESC
            """
        )
        return [
            VisitaResumen(
                desc_pagina=r["DESC_PAGINA"],
                total_visitas=r["total"],
                ultimo_acceso=r.get("ultimo_acceso"),
            )
            for r in cursor.fetchall()
        ]
