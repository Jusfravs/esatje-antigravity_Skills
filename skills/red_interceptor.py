# skills/red_interceptor.py
import asyncio
import logging
from playwright.async_api import async_playwright
import pandas as pd

logger = logging.getLogger(__name__)

BUSQUEDA_URL = "https://procesosjudiciales.funcionjudicial.gob.ec/busqueda"


async def extraer_via_red(numero_juicio: str) -> pd.DataFrame:
    resultados = []

    async def capturar_respuesta(response):
        url = response.url.lower()
        content_type = response.headers.get("content-type", "")

        if response.status != 200 or "application/json" not in content_type:
            return

        if "api" not in url and "search" not in url and "procesos" not in url:
            return

        try:
            data = await response.json()
            if isinstance(data, (dict, list)):
                resultados.append(data)
        except Exception:
            logger.debug("Error parsing JSON from intercepted response", exc_info=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("response", capturar_respuesta)

        await page.goto(BUSQUEDA_URL, wait_until="domcontentloaded")
        await page.wait_for_selector('input[placeholder*="Escriba palabras claves"]', timeout=15000)

        input_locator = page.locator('input[placeholder*="Escriba palabras claves"]').first
        await input_locator.fill(numero_juicio.strip())

        boton = page.get_by_role("button", name="Buscar")
        if await boton.count() == 0:
            boton = page.locator('button[type="submit"]').first

        await boton.click()

        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            logger.debug("networkidle not reached within timeout", exc_info=False)

        await browser.close()

    return pd.DataFrame(resultados)