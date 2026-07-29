# skills/esatje_interceptor/interceptor.py
"""
Skill: ESATJE Network & DOM Interceptor
Extrae información de procesos judiciales en E-SATJE mediante intercepción de red XHR/Fetch
y fallback a DOM con esperas explícitas (Zero time.sleep rule).
"""

import asyncio
import logging
import pandas as pd
from playwright.async_api import async_playwright

BUSQUEDA_URL = "https://procesosjudiciales.funcionjudicial.gob.ec/busqueda"

logger = logging.getLogger(__name__)


async def extraer_via_red(numero_juicio: str, timeout_ms: int = 15000) -> pd.DataFrame:
    """
    Ruta Primaria: Intercepta tráfico XHR/Fetch nativo en JSON de la API judicial.
    Retorna un DataFrame de Pandas con la respuesta JSON cruda o DataFrame vacío.
    """
    resultados = []

    async def capturar_respuesta(response):
        url = response.url.lower()
        content_type = response.headers.get("content-type", "")

        if response.status != 200 or "application/json" not in content_type:
            return

        if any(patron in url for patron in ["api", "search", "procesos", "expedientes", "actuaciones"]):
            try:
                data = await response.json()
                if isinstance(data, (dict, list)):
                    resultados.append(data)
            except Exception:
                logger.debug("Fallo al parsear JSON en respuesta interceptada", exc_info=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        page.on("response", capturar_respuesta)

        try:
            try:
                await page.goto(BUSQUEDA_URL, wait_until="domcontentloaded", timeout=timeout_ms)

                # Selector explícito sin time.sleep
                input_selector = 'input[placeholder*="Escriba palabras claves"], input[placeholder*="códigoDependencia-Año-Secuencial"], input[formcontrolname="numeroJuicio"]'
                await page.wait_for_selector(input_selector, timeout=timeout_ms, state="visible")
            except Exception:
                logger.debug("Error al cargar la página o esperar selector", exc_info=True)

            input_locator = page.locator(input_selector).first
            await input_locator.fill(numero_juicio.strip())

            boton = page.get_by_role("button", name="Buscar")
            if await boton.count() == 0:
                boton = page.locator('button[type="submit"], button:has-text("BUSCAR")').first

            await boton.click()

            # Espera explícita por respuesta de red
            try:
                await page.wait_for_load_state("networkidle", timeout=timeout_ms)
            except Exception:
                logger.debug("Timeout/Advertencia: networkidle no alcanzado", exc_info=False)

        finally:
            await browser.close()

    if resultados:
        # Convertir a DataFrame normalizado
        dfs = []
        for res in resultados:
            if isinstance(res, dict):
                datos = res.get("data", res)
                if isinstance(datos, list):
                    dfs.append(pd.json_normalize(datos))
                elif isinstance(datos, dict):
                    dfs.append(pd.json_normalize([datos]))
            elif isinstance(res, list):
                dfs.append(pd.json_normalize(res))
        
        if dfs:
            df_final = pd.concat(dfs, ignore_index=True)
            return df_final

    return pd.DataFrame()
