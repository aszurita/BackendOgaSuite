import logging

logger = logging.getLogger(__name__)


def get_usuarios(conn) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                codigo, nombres, apellido_paterno, apellido_materno,
                direccion_email, fecha_ingreso, departamento,
                Perfil_Cargo, ID_CONOCIMIENTO, rol_global,
                CODIGO_ROL_FUNCION, CODIGO_ROL_DATOS, ESTADO,
                centro_costo, puesto, localidad
            FROM T_DataUser_DataCitizen_Empresa
            WHERE departamento != 'JUBILADOS'
            ORDER BY nombres
            """
        )
        return cursor.fetchall()


def update_usuario(conn, codigo: str, payload: dict) -> None:
    if not payload:
        return
    cols = ", ".join(f"`{k}` = %s" for k in payload)
    vals = list(payload.values()) + [codigo]
    with conn.cursor() as cursor:
        cursor.execute(
            f"UPDATE T_DataUser_DataCitizen_Empresa SET {cols} WHERE codigo = %s",
            vals,
        )
    conn.commit()


def update_usuario_estado(conn, codigo: str, estado: str) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE T_DataUser_DataCitizen_Empresa SET ESTADO = %s WHERE codigo = %s",
            (estado, codigo),
        )
    conn.commit()
