import logging

logger = logging.getLogger(__name__)


def get_catalogo_referencia(conn) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                CAT.vista          AS Vista,
                CAT.codigo         AS Codigo,
                CAT.descripcion    AS Descripcion,
                CAT.tipo_catalogo  AS TipoCatalogo,
                CAT.detalle        AS Detalle,
                CAT.plataforma     AS Plataforma,
                CAT.servidor       AS Servidor,
                CAT.base           AS Base,
                CAT.esquema        AS Esquema,
                CAT.tabla          AS Tabla,
                EMP.nombre         AS Responsable,
                CAT.validado       AS Validado,
                CAT.observacion    AS Observacion,
                CAT.script         AS Script
            FROM vw_oga_catalogo CAT
            LEFT JOIN dw_dim_colaboradores EMP ON CAT.responsable = EMP.codigo_empleado
            """
        )
        return cursor.fetchall()


def get_catalogo_detalle(conn, codigo: str) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT codigo AS CODIGO, descripcion AS DESCRIPCION, codigosuperior AS CODIGOSUPERIOR
            FROM t_oga_catalogo_det
            WHERE codigosuperior = %s
            ORDER BY codigo
            """,
            (codigo,),
        )
        return cursor.fetchall()
