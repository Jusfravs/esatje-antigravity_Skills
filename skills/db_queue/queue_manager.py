# skills/db_queue/queue_manager.py
"""
Skill: SQLite Transactional Queue Manager
Gestiona la cola de tareas, reservas atómicas, estados de ejecución y persistencia de resultados en SQLite.
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

DEFAULT_DB_PATH = Path("esatje_antigravity.db")


class DBQueueManager:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.inicializar_bd()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=30.0)

    @contextmanager
    def _connection(self):
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @contextmanager
    def _exclusive_transaction(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def inicializar_bd(self):
        """Crea las tablas DDL transaccionales de expedientes, reserva y auditoría."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS expedientes_judiciales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_juicio TEXT UNIQUE,
                    datos_completos_json TEXT,
                    actualizado_en DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reserva_transacciones (
                    id_reserva INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_juicio TEXT UNIQUE,
                    estado TEXT CHECK(estado IN ('PENDIENTE', 'EN_PROCESO', 'EXITO', 'ERROR')),
                    reintentos INTEGER DEFAULT 0,
                    fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS log_auditoria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_juicio TEXT,
                    nivel TEXT,
                    mensaje TEXT,
                    creado_en DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            # Migración mínima: asegurar columna `reintentos` existe en reserva_transacciones
            cursor.execute("PRAGMA table_info('reserva_transacciones')")
            cols = [row[1] for row in cursor.fetchall()]
            if 'reintentos' not in cols:
                cursor.execute("ALTER TABLE reserva_transacciones ADD COLUMN reintentos INTEGER DEFAULT 0")
                conn.commit()
            # Verificar que la restricción CHECK sobre `estado` incluye 'EN_PROCESO'.
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='reserva_transacciones'")
            row = cursor.fetchone()
            if row:
                create_sql = row[0] or ''
                if "EN_PROCESO" not in create_sql:
                    # Reconstruir la tabla con el CHECK correcto preservando datos
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS reserva_transacciones_new (
                            id_reserva INTEGER PRIMARY KEY AUTOINCREMENT,
                            numero_juicio TEXT UNIQUE,
                            estado TEXT CHECK(estado IN ('PENDIENTE', 'EN_PROCESO', 'EXITO', 'ERROR')),
                            reintentos INTEGER DEFAULT 0,
                            fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    # Copiar datos, normalizando estado a 'PENDIENTE' si tuviera valores inválidos
                    cursor.execute('''
                        INSERT OR REPLACE INTO reserva_transacciones_new (id_reserva, numero_juicio, estado, reintentos, fecha_actualizacion)
                        SELECT id_reserva, numero_juicio,
                               CASE WHEN estado IN ('PENDIENTE','EXITO','ERROR') THEN estado ELSE 'PENDIENTE' END as estado,
                               COALESCE(reintentos, 0), fecha_actualizacion
                        FROM reserva_transacciones
                    ''')
                    cursor.execute('DROP TABLE reserva_transacciones')
                    cursor.execute('ALTER TABLE reserva_transacciones_new RENAME TO reserva_transacciones')
                    conn.commit()

            # Asegurar columna `actualizado_en` en expedientes_judiciales (migración mínima)
            cursor.execute("PRAGMA table_info('expedientes_judiciales')")
            exp_cols = [r[1] for r in cursor.fetchall()]
            if 'actualizado_en' not in exp_cols:
                cursor.execute("ALTER TABLE expedientes_judiciales ADD COLUMN actualizado_en DATETIME DEFAULT CURRENT_TIMESTAMP")
                conn.commit()

    def poblar_causas(self, causas: List[str]):
        """Pobla masivamente la tabla de reserva en estado PENDIENTE."""
        registros = [(str(c).strip(),) for c in causas if str(c).strip()]
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT INTO reserva_transacciones (numero_juicio, estado, reintentos)
                VALUES (?, 'PENDIENTE', 0)
                ON CONFLICT(numero_juicio) DO NOTHING
            ''', registros)
            conn.commit()

    def obtener_siguiente_pendiente(self) -> Optional[str]:
        """Reserva atómicamente el siguiente expediente pendiente."""
        with self._exclusive_transaction() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT numero_juicio FROM reserva_transacciones
                WHERE estado = 'PENDIENTE'
                ORDER BY id_reserva ASC LIMIT 1
            ''')
            row = cursor.fetchone()
            if not row:
                return None
            
            numero_juicio = row[0]
            cursor.execute('''
                UPDATE reserva_transacciones
                SET estado = 'EN_PROCESO', fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE numero_juicio = ?
            ''', (numero_juicio,))
            return numero_juicio

    def registrar_extraccion(self, numero_juicio: str, df_limpio: pd.DataFrame):
        """Registra el resultado de la extracción y actualiza el estado a EXITO de forma atómica."""
        datos_json = df_limpio.to_json(orient="records")
        with self._exclusive_transaction() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO expedientes_judiciales (numero_juicio, datos_completos_json, actualizado_en)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(numero_juicio) DO UPDATE SET
                    datos_completos_json = excluded.datos_completos_json,
                    actualizado_en = CURRENT_TIMESTAMP
            ''', (numero_juicio, datos_json))

            cursor.execute('''
                INSERT INTO reserva_transacciones (numero_juicio, estado, fecha_actualizacion)
                VALUES (?, 'EXITO', CURRENT_TIMESTAMP)
                ON CONFLICT(numero_juicio) DO UPDATE SET
                    estado = 'EXITO',
                    fecha_actualizacion = CURRENT_TIMESTAMP
            ''', (numero_juicio,))

    def registrar_error(self, numero_juicio: str, error_msg: str):
        """Registra el fallo de extracción e incrementa contador de reintentos."""
        with self._exclusive_transaction() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO reserva_transacciones (numero_juicio, estado, reintentos, fecha_actualizacion)
                VALUES (?, 'ERROR', 1, CURRENT_TIMESTAMP)
                ON CONFLICT(numero_juicio) DO UPDATE SET
                    estado = 'ERROR',
                    reintentos = reintentos + 1,
                    fecha_actualizacion = CURRENT_TIMESTAMP
            ''', (numero_juicio,))

            cursor.execute('''
                INSERT INTO log_auditoria (numero_juicio, nivel, mensaje)
                VALUES (?, 'ERROR', ?)
            ''', (numero_juicio, str(error_msg)))

    def obtener_estadisticas(self) -> Dict[str, int]:
        """Obtiene un diccionario con el conteo de causas por estado."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT estado, COUNT(*) FROM reserva_transacciones GROUP BY estado
            ''')
            return dict(cursor.fetchall())

    def reiniciar_errores(self, max_reintentos: int = 3) -> int:
        """Reinicia las causas en estado ERROR a PENDIENTE si no han superado max_reintentos."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE reserva_transacciones
                SET estado = 'PENDIENTE', fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE estado = 'ERROR' AND reintentos < ?
            ''', (max_reintentos,))
            conn.commit()
            return cursor.rowcount
