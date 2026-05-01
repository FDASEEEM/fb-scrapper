import asyncio
import logging
import os
import re
from typing import List, Dict
from playwright.async_api import async_playwright, Page
from src.config import settings

logger = logging.getLogger(__name__)

STATE_FILE = "fb_state.json"


class FacebookMarketplaceScraper:
    def __init__(self):
        self.cities = [
            c.strip().lower().replace(" ", "-")
            for c in settings.marketplace_cities.split(",")
            if c.strip()
        ]
        self.keywords = [
            k.strip()
            for k in settings.search_keywords.split(",")
            if k.strip()
        ]
        self.categories = [
            c.strip()
            for c in settings.search_categories.split(",")
            if c.strip()
        ]

    async def login(self, page: Page) -> bool:
        try:
            logger.info("Iniciando sesión en Facebook...")

            # Navegar a login con timeout mayor y esperar solo a que el DOM esté listo
            await page.goto(
                "https://www.facebook.com/login",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            logger.info("Página de login cargada")

            # Aceptar cookies si aparece el banner
            try:
                accept_btn = await page.wait_for_selector(
                    'button[data-testid="cookie-policy-manage-dialog-accept-button"]',
                    timeout=5000,
                )
                if accept_btn:
                    await accept_btn.click()
                    await asyncio.sleep(1)
                    logger.info("Cookies aceptadas")
            except Exception:
                pass

            # Rellenar credenciales vía JavaScript (más robusto contra bloqueos)
            await asyncio.sleep(2)
            await page.evaluate(
                """([email, password]) => {
                    const emailInput = document.querySelector('#email') || document.querySelector('input[name="email"]');
                    const passInput = document.querySelector('#pass') || document.querySelector('input[name="pass"]');
                    if (emailInput) { emailInput.value = email; emailInput.dispatchEvent(new Event('input', { bubbles: true })); }
                    if (passInput) { passInput.value = password; passInput.dispatchEvent(new Event('input', { bubbles: true })); }
                }""",
                [settings.fb_email, settings.fb_password],
            )
            logger.info("Credenciales ingresadas vía JS, enviando formulario...")

            # Hacer click en el botón de login vía JS también
            await page.evaluate(
                """() => {
                    const btn = document.querySelector('button[name="login"]') || document.querySelector('[type="submit"]');
                    if (btn) btn.click();
                }"""
            )

            # Esperar navegación post-login
            await page.wait_for_load_state("domcontentloaded", timeout=60000)
            await asyncio.sleep(3)

            logger.info(f"URL tras login: {page.url}")

            # Guardar screenshot de debug si hay problemas
            if "checkpoint" in page.url or "two_factor" in page.url:
                await page.screenshot(path="debug_checkpoint.png")
                logger.error(
                    "Facebook requiere verificación adicional (checkpoint/2FA). "
                    "Screenshot guardado en debug_checkpoint.png. "
                    "Resuélvela manualmente una vez desde tu IP habitual."
                )
                return False

            if "login" in page.url:
                await page.screenshot(path="debug_login_failed.png")
                logger.error(
                    "Login fallido: aún en página de login. "
                    "Screenshot guardado en debug_login_failed.png"
                )
                return False

            logger.info("Login exitoso")
            return True
        except Exception as e:
            logger.error(f"Error en login: {e}")
            try:
                await page.screenshot(path="debug_error.png")
                logger.info("Screenshot de error guardado en debug_error.png")
            except Exception:
                pass
            return False

    async def search_city(self, page: Page, city: str, keyword: str) -> List[Dict]:
        items: List[Dict] = []
        try:
            # Construir URL de búsqueda de Marketplace
            url = (
                f"https://www.facebook.com/marketplace/{city}/search/"
                f"?query={keyword}&radius={settings.search_radius_km}"
            )
            logger.info(
                f"Buscando: '{keyword}' en '{city}' "
                f"(radio {settings.search_radius_km}km)"
            )

            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(8)

            # Si redirige a login completo, no se puede buscar
            if "login" in page.url:
                logger.warning("Facebook redirigió a login. No se puede buscar sin sesión.")
                return items

            # Cerrar modal de "Ve más en Facebook" si aparece
            try:
                close_selectors = [
                    '[aria-label="Cerrar"]',
                    '[data-testid="dialog-close-button"]',
                    'div[role="dialog"] div[role="button"]',
                    'div[aria-label="Cerrar"]',
                ]
                for sel in close_selectors:
                    close_btn = await page.query_selector(sel)
                    if close_btn:
                        await close_btn.click()
                        await asyncio.sleep(2)
                        logger.info("Modal de login cerrado")
                        break
            except Exception:
                pass

            await page.screenshot(path=f"debug_search_{city}.png")

            # Scroll para cargar más items
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

            # Extraer links de items
            links = await page.query_selector_all('a[href*="/marketplace/item/"]')
            seen_ids = set()

            for link in links[: settings.max_items_per_search * 2]:
                try:
                    href = await link.get_attribute("href")
                    if not href or "/marketplace/item/" not in href:
                        continue

                    match = re.search(r"/marketplace/item/(\d+)", href)
                    if not match:
                        continue

                    item_id = match.group(1)
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                    # Extraer texto del card
                    text = await link.inner_text()
                    lines = [l.strip() for l in text.split("\n") if l.strip()]

                    title = lines[0] if lines else "Sin título"
                    price = lines[1] if len(lines) > 1 else "Precio no disponible"
                    location = lines[2] if len(lines) > 2 else city

                    # Intentar obtener imagen
                    img_el = await link.query_selector("img")
                    image_url = await img_el.get_attribute("src") if img_el else ""

                    items.append(
                        {
                            "id": item_id,
                            "title": title,
                            "price": price,
                            "location": location,
                            "link": (
                                f"https://www.facebook.com{href}"
                                if href.startswith("/")
                                else href
                            ),
                            "image_url": image_url,
                            "description": "",
                            "city": city,
                            "keyword": keyword,
                        }
                    )

                    if len(items) >= settings.max_items_per_search:
                        break
                except Exception as e:
                    logger.debug(f"Error extrayendo item: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error buscando en '{city}': {e}")

        logger.info(
            f"Encontrados {len(items)} items en '{city}' para '{keyword}'"
        )
        return items

    async def run(self) -> List[Dict]:
        all_items: List[Dict] = []

        if not self.keywords:
            logger.warning("No hay keywords configuradas.")
            return all_items

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=settings.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--window-size=1920,1080",
                    "--start-maximized",
                ],
            )

            # Intentar cargar estado previo si existe
            context_options = dict(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="es-CL",
                timezone_id="America/Santiago",
            )
            if os.path.exists(STATE_FILE):
                context_options["storage_state"] = STATE_FILE
                logger.info("Cargando sesión previa guardada...")

            context = await browser.new_context(**context_options)
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = await context.new_page()

            try:
                # Si existe sesión guardada, intentar usarla
                logged_in = False
                if os.path.exists(STATE_FILE):
                    await page.goto("https://www.facebook.com", timeout=15000)
                    await asyncio.sleep(2)
                    if "login" not in page.url:
                        logger.info("Sesión previa válida")
                        logged_in = True
                    else:
                        logger.info("Sesión expirada, se buscará sin login")

                if not logged_in:
                    logger.info("Buscando en Marketplace sin login...")

                for city in self.cities:
                    for keyword in self.keywords:
                        city_items = await self.search_city(page, city, keyword)
                        all_items.extend(city_items)
                        await asyncio.sleep(2)
            finally:
                await browser.close()

        return all_items
