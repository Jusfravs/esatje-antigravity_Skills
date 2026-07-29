---
name: pandas-data-cleaner
description: "Skill para la normalización, sanitización y estandarización de DataFrames de Pandas en pipelines de procesamiento de datos agénticos."
---

# Skill: Pandas Data Cleaner

Lanza procesos de limpieza determinista sobre esquemas de datos extraídos por agentes.

## Reglas de Transformación
1. **Normalización de Cabeceras**: Conversión a UPPERCASE, reemplazo de espacios/puntos por guiones bajos `_`, eliminación de caracteres no alfanuméricos.
2. **Sanitización de Celdas**: Remoción de tildes (NFD), eliminación de caracteres de control, trim de espacios en blanco.
3. **Persistencia de Tipos**: Preservación de valores nulos reales (`NaN`/`None`) sin convertirlos en strings `"NaN"`.

## Ejemplo de uso
```python
from skills.data_cleaner.cleaner import normalizar_columnas

df_limpio = normalizar_columnas(df_crudo)
```
