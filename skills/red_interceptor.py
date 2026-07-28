# skills/red_interceptor.py
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
                    pass  # Respuesta no relevante, se ignora silenciosamente

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # El listener se registra ANTES de la navegación
        page.on("response", capturar_respuesta)

        await page.goto("https://esatje.funcionjudicial.gob.ec/", wait_until="networkidle")
        await page.fill('input[name="numeroJuicio"]', numero_juicio)
        await page.click('button[type="submit"]')

        # Freno de ejecución dinámico, sin tiempos fijos
        await page.wait_for_event("response", timeout=15000)
        await browser.close()

    return pd.DataFrame(resultados)