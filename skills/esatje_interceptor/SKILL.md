---
name: esatje-interceptor
description: "Reglas y herramientas para la intercepción de red XHR/Fetch y extracción con Playwright en el portal e-SATJE de la Función Judicial del Ecuador."
---

# Skill: ESATJE Network Interceptor

Skill agéntica para la extracción resiliente de expedientes judiciales desde E-SATJE (Angular SPA).

## Principios Fundamentales

1. **Regla de Oro (Zero Sleep Rule)**:
   - Prohibido el uso de `time.sleep()` o `asyncio.sleep()`.
   - Utilizar únicamente esperas explícitas impulsadas por eventos: `page.wait_for_selector()`, `page.wait_for_event("response")` o `wait_until="networkidle"`.

2. **Ruta Primaria (XHR/Fetch Interception)**:
   - Registrar los listeners de eventos de red `page.on("response", callback)` **antes** de realizar cualquier acción de navegación o submit.
   - Convertir directamente los JSONs interceptados a DataFrames de Pandas evitando el overhead de renderizado e inspección del DOM.

3. **Ruta de Respaldo (DOM Sync)**:
   - Activar únicamente si la intercepción de red no produce objetos JSON utilizables o la API requiere tokens dinámicos.
   - Detener el scraping hasta confirmar la hidratación con el selector de anclaje: `text="Actor/Ofendido:"` con `state='visible'`.

## Checklist de Verificación
- [ ] Listener registrado antes de la acción
- [ ] Cero esperas por temporizador fijo
- [ ] Manejo de excepciones en bloque try/finally para garantizar cierre de navegador
- [ ] Retorno de un DataFrame de Pandas estructurado
