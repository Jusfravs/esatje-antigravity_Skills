---
name: sqlite-queue-manager
description: "Skill transaccional en SQLite para la reserva atómica, control de estados (PENDIENTE, EN_PROCESO, EXITO, ERROR) y persistencia de resultados."
---

# Skill: SQLite Queue Manager

Módulo de persistencia y cola transaccional resiliente para workflows agénticos.

## Capacidades y Transaccionalidad
- **Reserva Atómica**: Usa `BEGIN IMMEDIATE` para prevenir condiciones de carrera (Race Conditions) al seleccionar la siguiente tarea `PENDIENTE`.
- **Control de Estados**: Mantiene el ciclo de vida de los registros y previene ejecuciones duplicadas.
- **Rollback Seguro**: Captura excepciones durante la inserción y registra fallos en la tabla `log_auditoria`.

## Uso
```python
from skills.db_queue.queue_manager import DBQueueManager

db = DBQueueManager()
juicio = db.obtener_siguiente_pendiente()
if juicio:
    # Procesar...
    db.registrar_extraccion(juicio, df_limpio)
```
