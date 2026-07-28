# skills/data_cleaner.py
import pandas as pd

def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica la normalización estándar de Antigravity a las cabeceras.
    """
    if df.empty:
        return df
        
    # Limpieza estricta: elimina espacios en blanco y convierte a mayúsculas
    df.columns = df.columns.str.strip().str.upper()
    
    return df