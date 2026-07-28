---
name: esatje-scraping-rules
description: "Reglas obligatorias para navegar y extraer datos del portal E-SATJE (SPA en Angular) con Playwright async. Usar esta skill siempre que se escriba, revise o modifique código de navegación, interceptación de red, o extracción de datos judiciales desde E-SATJE dentro del proyecto Antigravity."
---

# Reglas de Extracción — E-SATJE

E-SATJE es una Single Page Application (SPA) de Angular con hidratación asíncrona: el HTML base carga antes que la información real del juicio. Estas reglas son estrictas y no negociables.

## Regla 0 — Prohibido `time.sleep()` y esperas fijas

Nunca uses `time.sleep()`, `asyncio.sleep()` como mecanismo de sincronización, ni scraping estático basado solo en `page.goto(url)` seguido de una extracción inmediata. Cualquier código que dependa de un tiempo fijo para "esperar a que cargue" es un defecto, no una solución temporal.

## Ruta primaria — Intercepción de red (siempre preferida)

Captura el tráfico XHR/Fetch nativo de la página (las respuestas JSON de la API de la Judicatura) y pasa esos datos crudos directamente a diccionarios y DataFrames de Pandas, **omitiendo por completo el parseo del DOM**.

```python
import asyncio
from playwright.async_api import async_playwright
import pandas as pd

async def extraer_via_red(numero_juicio: str) -> pd.DataFrame:
    resultados = []

    async def capturar_respuesta(response):
        if "api/" in response.url and response.status == 200:
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    data = await response.json()
                    resultados.append(data)
                except Exception:
                    pass  # respuesta no relevante, no es un error de negocio

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("response", capturar_respuesta)

        await page.goto("https://esatje.funcionjudicial.gob.ec/", wait_until="networkidle")
        await page.fill('input[name="numeroJuicio"]', numero_juicio)
        await page.click('button[type="submit"]')

        # Esperar explícitamente a que la API responda, no un sleep fijo
        await page.wait_for_event("response", timeout=15000)
        await browser.close()

    return pd.DataFrame(resultados)
```

Reglas dentro de esta ruta:
- El listener de `response` debe registrarse **antes** de disparar la navegación o la búsqueda, nunca después.
- Si la respuesta no es JSON o no coincide con el patrón de la API, se ignora silenciosamente — no se lanza excepción de negocio por ello.
- El JSON crudo interceptado va directo a un diccionario/DataFrame; no se re-extrae la misma información desde el DOM "para confirmar".

## Ruta secundaria — Fallback sincronizado por DOM

Se usa **únicamente** si la red está ofuscada (respuestas encriptadas, endpoints no identificables, o cambios en el contrato de la API). Combina Playwright + BeautifulSoup4 bajo un embudo estricto de esperas explícitas:

1. Cargar la URL base.
2. Ingresar el input `numeroJuicio`.
3. Ejecutar la búsqueda esperando la visibilidad de la grilla de resultados.
4. Hacer clic en el expediente.
5. Activar el freno de ejecución real con el selector exacto de confirmación:

```python
await page.wait_for_selector('text="Actor/Ofendido:"', state='visible')
# Solo después de esta línea es seguro extraer el HTML
html = await page.content()
```

Este selector (`text="Actor/Ofendido:"` con `state='visible'`) es el marcador oficial de que los datos reales del juicio ya se hidrataron. No sustituir por otro selector "similar" sin validar primero contra el HTML real.

## Checklist antes de dar por válida una extracción

- [ ] ¿Se intentó primero la ruta de intercepción de red?
- [ ] ¿No hay ningún `sleep()` fijo en el flujo, ni en la ruta primaria ni en la secundaria?
- [ ] Si se usó la ruta DOM, ¿se esperó explícitamente el selector `Actor/Ofendido:` antes de extraer?
- [ ] ¿El resultado (dict/DataFrame) pasa a la skill `pandas-normalizacion` antes de cualquier filtro?
