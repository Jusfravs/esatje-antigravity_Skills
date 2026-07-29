# db_manager.py
"""
Wrapper de compatibilidad para el gestor de base de datos.
Delega en la skill `skills.db_queue.queue_manager.DBQueueManager`.
"""
import pandas as pd
from pathlib import Path
from skills.db_queue.queue_manager import DBQueueManager, DEFAULT_DB_PATH

_db_instance = DBQueueManager(DEFAULT_DB_PATH)


def inicializar_bd():
    _db_instance.inicializar_bd()


def registrar_extraccion(numero_juicio: str, df_limpio: pd.DataFrame):
    _db_instance.registrar_extraccion(numero_juicio, df_limpio)


def registrar_error(numero_juicio: str, error_msg: str):
    _db_instance.registrar_error(numero_juicio, error_msg)


def poblar_causas(causas):
    _db_instance.poblar_causas(causas)


def obtener_estadisticas():
    return _db_instance.obtener_estadisticas()


def reiniciar_errores(max_reintentos: int = 3) -> int:
    return _db_instance.reiniciar_errores(max_reintentos=max_reintentos)


def obtener_siguiente_pendiente():
    return _db_instance.obtener_siguiente_pendiente()


# Exponer la instancia si se necesita acceso directo
db = _db_instance