import asyncio
import logging
import sys
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.scraper import FacebookMarketplaceScraper
from src.telegram_bot import send_item
from src.redis_client import is_processed, mark_processed
from src.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def check_marketplace():
    logger.info("=== Iniciando revisión de Facebook Marketplace ===")

    if not settings.search_keywords:
        logger.warning(
            "No hay keywords configuradas. "
            "Configura SEARCH_KEYWORDS en las variables de entorno."
        )
        return

    scraper = FacebookMarketplaceScraper()
    items = await scraper.run()

    new_items = 0
    for item in items:
        if not is_processed(item["id"]):
            try:
                await send_item(
                    title=item["title"],
                    price=item["price"],
                    description=item.get("description", ""),
                    location=item["location"],
                    image_url=item.get("image_url", ""),
                    link=item["link"],
                )
                mark_processed(item["id"])
                new_items += 1
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error procesando item {item['id']}: {e}")

    logger.info(
        f"=== Revisión completada. {new_items} nuevos items enviados ==="
    )


async def main():
    logger.info("Iniciando FB Marketplace Scraper...")
    logger.info(f"Ciudades: {settings.marketplace_cities}")
    logger.info(f"Keywords: {settings.search_keywords}")
    logger.info(f"Intervalo: {settings.check_interval_minutes} minutos")

    # Ejecutar inmediatamente la primera vez
    await check_marketplace()

    # Configurar scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_marketplace,
        trigger=IntervalTrigger(minutes=settings.check_interval_minutes),
        id="marketplace_check",
        replace_existing=True,
    )
    scheduler.start()

    # Mantener vivo el proceso
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
