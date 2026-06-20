#!/usr/bin/env python3
"""Abre Chromium, logueate en Facebook, cerrá el navegador.
La sesión se guarda automáticamente al cerrar la ventana."""

import asyncio

from playwright.async_api import async_playwright

SAVE_PATH = "data/facebook_auth.json"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized"],
        )
        ctx = await browser.new_context(no_viewport=True)
        page = await ctx.new_page()
        await page.goto("https://www.facebook.com/", timeout=120000)

        print("\n🔓 LOGUEATE en Facebook en la ventana que se abrió.")
        print("❌ CERRÁ la ventana del navegador cuando termines.")
        print("💾 La sesión se guarda automáticamente.\n", flush=True)

        # Wait until pages stay 0 for 3 consecutive checks (avoids false positives
        # during navigation redirects)
        empty_count = 0
        while empty_count < 3:
            try:
                if len(ctx.pages) == 0:
                    empty_count += 1
                else:
                    empty_count = 0
                await asyncio.sleep(1)
            except Exception:
                break

        await ctx.storage_state(path=SAVE_PATH)
        print(f"✅ Sesión guardada en {SAVE_PATH}", flush=True)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
