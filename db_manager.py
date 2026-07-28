# db_manager.py
import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("esatje_antigravity.db")

def inicializar_bd():
    """
    Crea las estructuras DDL si no existen, garantizando la tabla de reserva.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabla principal de datos extraídos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expedientes_judiciales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_juicio TEXT UNIQUE,
            datos_completos_json TEXT
        )
    ''')
    
    # Tabla transaccional obligatoria para el control de la cola (Reserva)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reserva_transacciones (
            id_reserva INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_juicio TEXT UNIQUE,
            estado TEXT CHECK(estado IN ('PENDIENTE', 'EXITO', 'ERROR')),
            fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def registrar_extraccion(numero_juicio: str, df_limpio: pd.DataFrame):
    """
    Inserta el DataFrame limpio y actualiza la reserva transaccional.
    Maneja el commit/rollback de forma segura.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Registrar los datos del expediente
        datos_json = df_limpio.to_json(orient="records")
        
        cursor.execute('''
            INSERT INTO expedientes_judiciales (numero_juicio, datos_completos_json)
            VALUES (?, ?)
            ON CONFLICT(numero_juicio) DO UPDATE SET datos_completos_json=excluded.datos_completos_json
        ''', (numero_juicio, datos_json))
        
        # 2. Confirmar el éxito en la tabla de reserva
        cursor.execute('''
            INSERT INTO reserva_transacciones (numero_juicio, estado)
            VALUES (?, 'EXITO')
            ON CONFLICT(numero_juicio) DO UPDATE SET estado='EXITO', fecha_actualizacion=CURRENT_TIMESTAMP
        ''', (numero_juicio,))
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        # 3. En caso de fallo estructural, registrar el error en la reserva
        cursor.execute('''
            INSERT INTO reserva_transacciones (numero_juicio, estado)
            VALUES (?, 'ERROR')
            ON CONFLICT(numero_juicio) DO UPDATE SET estado='ERROR', fecha_actualizacion=CURRENT_TIMESTAMP
        ''', (numero_juicio,))
        conn.commit()
        raise e
        
    finally:
        conn.close()