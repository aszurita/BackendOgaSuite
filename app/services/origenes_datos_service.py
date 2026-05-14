import logging

logger = logging.getLogger(__name__)


def get_servidores(conn) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                S.txt_servidor AS servidor,
                COUNT(DISTINCT S.txt_host) AS bases_de_datos,
                COUNT(DISTINCT CONCAT(S.txt_host, '.', IFNULL(S.txt_fuente_esquema, ''))) AS esquemas,
                COUNT(DISTINCT CASE WHEN L.desc_tecnica_tabla IS NULL THEN NULL
                                    ELSE CONCAT(S.txt_host, '.', IFNULL(S.txt_fuente_esquema, ''), '.', L.desc_tecnica_tabla)
                               END) AS tablas,
                COUNT(DISTINCT CASE WHEN L.desc_tecnica_atributo IS NULL THEN NULL
                                    ELSE CONCAT(S.txt_host, '.', IFNULL(S.txt_fuente_esquema, ''), '.', L.desc_tecnica_tabla, '.', L.desc_tecnica_atributo)
                               END) AS campos,
                CASE WHEN COUNT(DISTINCT S.txt_host) = 0 THEN 0 ELSE 1 END AS servidor_activo
            FROM t_fuente_aprovisionamiento S
            LEFT JOIN t_atributos_inf_tecnica_larga L
                ON S.id_fuente_aprovisionamiento = L.id_fuente_aprovisionamiento
            WHERE S.txt_servidor IS NOT NULL AND S.sn_activo = '1'
            GROUP BY S.txt_servidor
            ORDER BY S.txt_servidor
            """
        )
        rows = cursor.fetchall()
        return [
            {
                "servidor":       r.get("servidor") or "",
                "bases_de_datos": int(r.get("bases_de_datos") or 0),
                "esquemas":       int(r.get("esquemas") or 0),
                "tablas":         int(r.get("tablas") or 0),
                "campos":         int(r.get("campos") or 0),
                "servidor_activo": int(r.get("servidor_activo") or 0),
            }
            for r in rows
        ]
