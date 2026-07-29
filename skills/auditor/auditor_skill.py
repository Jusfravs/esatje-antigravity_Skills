# skills/auditor/auditor_skill.py
"""
Skill: Quality & Integrity Auditor
Valida la integridad de la base de datos, el cumplimiento de reglas y genera reportes de auditoría.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def auditar_base_datos(db_path: Path) -> Dict[str, Any]:
    """Valida la integridad de registros y coherencia en las tablas SQLite."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    reporte = {
        "total_expedientes_guardados": 0,
        "total_reserva": 0,
        "conteo_por_estado": {},
        "errores_registrados": 0,
        "salud_porcentaje": 0.0
    }

    try:
        cursor.execute("SELECT COUNT(*) FROM expedientes_judiciales")
        reporte["total_expedientes_guardados"] = cursor.fetchone()[0]
    except Exception:
        logger.exception("Error al contar expedientes_judiciales")

    try:
        cursor.execute("SELECT COUNT(*) FROM reserva_transacciones")
        reporte["total_reserva"] = cursor.fetchone()[0]

        cursor.execute("SELECT estado, COUNT(*) FROM reserva_transacciones GROUP BY estado")
        reporte["conteo_por_estado"] = dict(cursor.fetchall())
    except Exception:
        logger.exception("Error al consultar reserva_transacciones")

    try:
        cursor.execute("SELECT COUNT(*) FROM log_auditoria WHERE nivel='ERROR'")
        reporte["errores_registrados"] = cursor.fetchone()[0]
    except Exception:
        logger.exception("Error al contar errores en log_auditoria")

    total = reporte["total_reserva"]
    exitos = reporte["conteo_por_estado"].get("EXITO", 0)
    reporte["salud_porcentaje"] = round((exitos / total * 100), 2) if total > 0 else 0.0

    conn.close()
    return reporte
