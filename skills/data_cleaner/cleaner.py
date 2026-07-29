# skills/data_cleaner/cleaner.py
"""
Skill: Pandas Data Cleaner & Normalizer
Procesa y normaliza DataFrames de Pandas provenientes de extracciones XHR/DOM.
"""

import re
import unicodedata
import pandas as pd


def normalizar_texto(texto: str) -> str:
    """Remueve tildes, caracteres especiales y convierte a mayúsculas limpias."""
    if not texto or pd.isna(texto):
        return ""
    texto = unicodedata.normalize('NFD', str(texto))
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.upper().strip()


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica la normalización estándar de Antigravity:
    - Limpia espacios en las cabeceras
    - Convierte cabeceras a mayúsculas
    - Remueve caracteres especiales en nombres de columnas
    - Limpia celdas de texto
    """
    if df.empty:
        return df

    # Normalizar nombres de columnas
    nuevas_columnas = []
    for col in df.columns:
        col_str = str(col).strip().upper()
        col_str = re.sub(r'[\s\.\-]+', '_', col_str)
        col_str = re.sub(r'[^A-Z0-9_]', '', col_str)
        nuevas_columnas.append(col_str)
    
    df.columns = nuevas_columnas

    # Limpiar contenido de texto en el DataFrame
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(lambda val: normalizar_texto(val) if isinstance(val, str) else val)

    return df
