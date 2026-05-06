import logging
from datetime import date, datetime
from app.models.campanias import (
    CampaniaClasificacion, CampaniaClasificacionCreate,
    CampaniaSeguimientoResumen, CampaniaStats,
)

logger = logging.getLogger(__name__)


def _es_terminado(estado: str | None, fecha_fin: datetime | None) -> bool:
    if estado and estado.upper() == "T":
        return True
    if isinstance(fecha_fin, datetime):
        fecha_fin = fecha_fin.date()
    if fecha_fin and fecha_fin < date.today():
        return True
    return False


def _split_iniciativas(value: str | None) -> list[str]:
    return [item.strip() for item in str(value or "").split("|") if item.strip()]


def get_clasificaciones(conn) -> list[CampaniaClasificacion]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT descrip_clasificacion, descripcion, subtipo, iniciativas,
                   Periodo AS periodo, activo, fecha_corte
            FROM t_campanias_clasificacion
            WHERE activo = 1
            ORDER BY descrip_clasificacion, subtipo
            """
        )
        clasificaciones_rows = cursor.fetchall()

        cursor.execute(
            "SELECT CodigoIniciativa, Estado, FechaFin FROM t_campanias_seguimiento"
        )
        seguimientos = cursor.fetchall()

    conteos: dict[str, dict] = {}
    for seg in seguimientos:
        codigo = seg.get("CodigoIniciativa")
        if not codigo:
            continue
        terminado = _es_terminado(seg.get("Estado"), seg.get("FechaFin"))
        if codigo not in conteos:
            conteos[codigo] = {"activos": 0, "terminados": 0}
        if terminado:
            conteos[codigo]["terminados"] += 1
        else:
            conteos[codigo]["activos"] += 1

    result = []
    for idx, row in enumerate(clasificaciones_rows, start=1):
        activos = 0
        terminados = 0
        for codigo in _split_iniciativas(row.get("iniciativas")):
            c = conteos.get(codigo, {"activos": 0, "terminados": 0})
            activos += c["activos"]
            terminados += c["terminados"]
        result.append(CampaniaClasificacion(
            id=idx,
            descripcion=row.get("descripcion"),
            descrip_clasificacion=row.get("descrip_clasificacion"),
            subtipo=row.get("subtipo"),
            iniciativas=row.get("iniciativas"),
            periodo=row.get("periodo"),
            activo=row.get("activo"),
            fecha_corte=row.get("fecha_corte"),
            tipo=row.get("descrip_clasificacion"),
            estado="A" if row.get("activo") else "I",
            num_activos=activos,
            num_terminados=terminados,
            num_total=activos + terminados,
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
        clasificaciones = get_clasificaciones(conn)
        match = next((c for c in clasificaciones if c.id == clasificacion_id), None)
        codigos = _split_iniciativas(match.iniciativas if match else None)
        if not codigos:
            return []
        placeholders = ", ".join(["%s"] * len(codigos))
        conditions.append(f"CodigoIniciativa IN ({placeholders})")
        params.extend(codigos)
    if estado:
        conditions.append("UPPER(IFNULL(Estado,'')) = UPPER(%s)")
        params.append(estado)

    where = " AND ".join(conditions)
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT CodigoIniciativa, Iniciativa, DescripcionNegocio, Estado,
                   FechaIni, FechaFin
            FROM t_campanias_seguimiento
            WHERE {where}
            ORDER BY Iniciativa
            """,
            params,
        )
        rows = cursor.fetchall()

    grupos: dict[str, dict] = {}
    for row in rows:
        nombre = row.get("Iniciativa")
        codigo = row.get("CodigoIniciativa") or f"ID_{nombre}"
        terminado = _es_terminado(row.get("Estado"), row.get("FechaFin"))

        if codigo not in grupos:
            grupos[codigo] = {
                "nombre": nombre,
                "descripcion_negocio": row.get("DescripcionNegocio"),
                "estado": row.get("Estado"),
                "fecha_inicio": row.get("FechaIni"),
                "fecha_fin": row.get("FechaFin"),
                "activos": 0,
                "terminados": 0,
                "valor": 0,
                "terminado": terminado,
            }
        if terminado:
            grupos[codigo]["terminados"] += 1
        else:
            grupos[codigo]["activos"] += 1
        grupos[codigo]["valor"] += 1

    return [
        CampaniaSeguimientoResumen(
            codigo_iniciativa=codigo,
            nombre=g["nombre"],
            descripcion_negocio=g["descripcion_negocio"],
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
        cursor.execute("SELECT COUNT(1) AS total FROM t_campanias_clasificacion WHERE activo = 1")
        total_clas = cursor.fetchone()["total"]

        params_seg: list = []
        where_seg = "1=1"
        if clasificacion_id:
            clasificaciones = get_clasificaciones(conn)
            match = next((c for c in clasificaciones if c.id == clasificacion_id), None)
            codigos = _split_iniciativas(match.iniciativas if match else None)
            if not codigos:
                return CampaniaStats(total_clasificaciones=total_clas)
            placeholders = ", ".join(["%s"] * len(codigos))
            where_seg = f"CodigoIniciativa IN ({placeholders})"
            params_seg.extend(codigos)

        cursor.execute(
            f"SELECT Estado, FechaFin FROM t_campanias_seguimiento WHERE {where_seg}",
            params_seg,
        )
        rows = cursor.fetchall()

    total = len(rows)
    terminadas = sum(1 for r in rows if _es_terminado(r.get("Estado"), r.get("FechaFin")))

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
            INSERT INTO t_campanias_clasificacion
                (descrip_clasificacion, descripcion, subtipo, iniciativas, Periodo, activo, fecha_corte)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                data.descrip_clasificacion or data.tipo or data.descripcion,
                data.descripcion,
                data.subtipo,
                data.iniciativas,
                data.periodo,
                data.activo if data.activo is not None else 1,
                data.fecha_corte,
            ],
        )
    clasificaciones = get_clasificaciones(conn)
    return clasificaciones[-1] if clasificaciones else CampaniaClasificacion(id=1, descripcion=data.descripcion)
