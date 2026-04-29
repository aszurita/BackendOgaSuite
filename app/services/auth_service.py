import logging
import pymysql.connections
from app.models.auth import (
    CurrentUser, UserInfo, PermissionsMap,
    GlosarioPermisos, MetadatosPermisos, AprobacionesPermisos,
    DominiosPermisos, CampaniasPermisos, MeResponse,
)
from app.core.cache import get_permisos_cache, get_permisos_lock

logger = logging.getLogger(__name__)


def _build_permissions(is_oga: bool) -> PermissionsMap:
    if is_oga:
        return PermissionsMap(
            glosario=GlosarioPermisos(can_create=True, can_edit=True, can_delete=True),
            metadatos=MetadatosPermisos(can_edit_direct=True, requires_approval=False),
            aprobaciones=AprobacionesPermisos(can_approve=True, can_reject=True),
            dominios=DominiosPermisos(can_create=True, can_edit=True),
            campanias=CampaniasPermisos(can_manage=True),
        )
    return PermissionsMap(
        glosario=GlosarioPermisos(),
        metadatos=MetadatosPermisos(can_edit_direct=False, requires_approval=True),
        aprobaciones=AprobacionesPermisos(),
        dominios=DominiosPermisos(),
        campanias=CampaniasPermisos(),
    )


def _get_empleado_data(conn: pymysql.connections.Connection, username: str) -> dict:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                CAST(CODIGO AS CHAR(50))       AS codigo,
                IFNULL(NOMBRES, '')            AS nombres,
                IFNULL(APELLIDOS, '')          AS apellidos,
                IFNULL(CENTRO_COSTO, '')       AS centro_costo,
                IFNULL(DEPARTAMENTO, '')       AS departamento,
                IFNULL(CARGO, '')              AS cargo,
                IFNULL(LOCALIDAD, '')          AS localidad
            FROM Tmp_DATOS_EMPLEADOS
            WHERE LOWER(TRIM(web_user)) = LOWER(%s)
            LIMIT 1
            """,
            [username],
        )
        row = cursor.fetchone()
    if not row:
        return {}
    return {
        "codigo_empleado": row.get("codigo"),
        "centro_costo":    row.get("centro_costo"),
        "departamento":    row.get("departamento"),
        "cargo":           row.get("cargo"),
        "localidad":       row.get("localidad"),
    }


def _check_is_oga(conn: pymysql.connections.Connection, email: str) -> bool:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(1) AS total FROM t_oga_usuarios
            WHERE LOWER(TRIM(email)) = LOWER(%s) AND sn_activo = 1
            """,
            [email],
        )
        row = cursor.fetchone()
    return bool(row and row.get("total", 0) > 0)


def enrich_user(conn: pymysql.connections.Connection, token_payload: dict) -> CurrentUser:
    """Construye CurrentUser enriquecido desde el token JWT y la BD, con cache TTL."""
    email = (
        token_payload.get("preferred_username")
        or token_payload.get("upn")
        or token_payload.get("email")
        or ""
    ).lower().strip()

    username = email.split("@")[0] if "@" in email else email
    display_name = token_payload.get("name", username)

    cache = get_permisos_cache()
    lock  = get_permisos_lock()

    with lock:
        cached = cache.get(email)
        if cached:
            return cached

    empleado    = _get_empleado_data(conn, username)
    is_oga      = _check_is_oga(conn, email)
    permissions = _build_permissions(is_oga)

    user = CurrentUser(
        email=email,
        display_name=display_name,
        username=username,
        is_oga=is_oga,
        permissions=permissions,
        **empleado,
    )

    with lock:
        cache[email] = user

    return user


def get_me_response(user: CurrentUser) -> MeResponse:
    return MeResponse(
        user=UserInfo(
            email=user.email,
            display_name=user.display_name,
            username=user.username,
            codigo_empleado=user.codigo_empleado,
            centro_costo=user.centro_costo,
            departamento=user.departamento,
            cargo=user.cargo,
            localidad=user.localidad,
        ),
        is_oga=user.is_oga,
        permissions=user.permissions or _build_permissions(False),
    )
