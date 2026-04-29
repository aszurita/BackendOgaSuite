import logging
from datetime import datetime
from app.models.campanias import (
    CampaniaClasificacion, CampaniaClasificacionCreate,
    CampaniaSeguimientoResumen, CampaniaStats,
)

logger = logging.getLogger(__name__)


def _es_terminado(estado: str | None, fecha_fin: datetime | None) -> bool:
    if estado and estado.upper() == "T":
        return True
    if fecha_fin and fecha_fin < datetime.now():
        return True
    return False


def get_clasificaciones(conn) -> list[CampaniaClasificacion]:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, descripcion, tipo, estado FROM t_campanias_clasificacion ORDER BY descripcion"
        )
        clasificaciones_rows = cursor.fetchall()

        cursor.execute(
            "SELECT id_clasificacion, estado, fecha_fin FROM t_campanias_seguimiento"
        )
        seguimientos = cursor.fetchall()

    conteos: dict[int, dict] = {}
    for seg in seguimientos:
        clas_id = seg["id_clasificacion"]
        terminado = _es_terminado(seg.get("estado"), seg.get("fecha_fin"))
        if clas_id not in conteos:
            conteos[clas_id] = {"activos": 0, "terminados": 0}
        if terminado:
            conteos[clas_id]["terminados"] += 1
        else:
            conteos[clas_id]["activos"] += 1

    result = []
    for row in clasificaciones_rows:
        c = conteos.get(row["id"], {"activos": 0, "terminados": 0})
        result.append(CampaniaClasificacion(
            id=row["id"],
            descripcion=row.get("descripcion"),
            tipo=row.get("tipo"),
            estado=row.get("estado"),
            num_activos=c["activos"],
            num_terminados=c["terminados"],
            num_total=c["activos"] + c["terminados"],
        ))
    return result


def get_seguimiento(
    conn,
    clasificacion_id: int | None = None,
    estado: str | None = None,
) -> list[CampaniaSeguimientoResumen]:
    conditions = ["1=1"]
    params: list = []

    if clasificacion_id:
        conditions.append("id_clasificacion = %s")
        params.append(clasificacion_id)
    if estado:
        conditions.append("UPPER(IFNULL(estado,'')) = UPPER(%s)")
        params.append(estado)

    where = " AND ".join(conditions)
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT codigo_iniciativa, nombre_iniciativa, estado,
                   fecha_inicio, fecha_fin, valor
            FROM t_campanias_seguimiento
            WHERE {where}
            ORDER BY nombre_iniciativa
            """,
            params,
        )
        rows = cursor.fetchall()

    grupos: dict[str, dict] = {}
    for row in rows:
        nombre = row.get("nombre_iniciativa")
        codigo = row.get("codigo_iniciativa") or f"ID_{nombre}"
        terminado = _es_terminado(row.get("estado"), row.get("fecha_fin"))

        if codigo not in grupos:
            grupos[codigo] = {
                "nombre": nombre,
                "estado": row.get("estado"),
                "fecha_inicio": row.get("fecha_inicio"),
                "fecha_fin": row.get("fecha_fin"),
                "activos": 0,
                "terminados": 0,
                "valor": 0,
                "terminado": terminado,
            }
        if terminado:
            grupos[codigo]["terminados"] += 1
        else:
            grupos[codigo]["activos"] += 1
        grupos[codigo]["valor"] += (row.get("valor") or 0)

    return [
        CampaniaSeguimientoResumen(
            codigo_iniciativa=codigo,
            nombre=g["nombre"],
            estado=g["estado"],
            num_activos=g["activos"],
            num_terminados=g["terminados"],
            valor=g["valor"],
            fecha_inicio=g["fecha_inicio"],
            fecha_fin=g["fecha_fin"],
            terminado=g["terminado"],
        )
        for codigo, g in grupos.items()
    ]


def get_estadisticas(conn, clasificacion_id: int | None = None) -> CampaniaStats:
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(1) AS total FROM t_campanias_clasificacion")
        total_clas = cursor.fetchone()["total"]

        params_seg: list = []
        where_seg = "1=1"
        if clasificacion_id:
            where_seg = "id_clasificacion = %s"
            params_seg.append(clasificacion_id)

        cursor.execute(
            f"SELECT estado, fecha_fin FROM t_campanias_seguimiento WHERE {where_seg}",
            params_seg,
        )
        rows = cursor.fetchall()

    total = len(rows)
    terminadas = sum(1 for r in rows if _es_terminado(r.get("estado"), r.get("fecha_fin")))

    return CampaniaStats(
        total_clasificaciones=total_clas,
        total_iniciativas=total,
        total_activas=total - terminadas,
        total_terminadas=terminadas,
    )


def crear_clasificacion(conn, data: CampaniaClasificacionCreate) -> CampaniaClasificacion:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO t_campanias_clasificacion (descripcion, tipo, estado)
            VALUES (%s, %s, %s)
            """,
            [data.descripcion, data.tipo, data.estado],
        )
        new_id = cursor.lastrowid
    clasificaciones = get_clasificaciones(conn)
    return next(
        (c for c in clasificaciones if c.id == new_id),
        CampaniaClasificacion(id=new_id, descripcion=data.descripcion),
    )
