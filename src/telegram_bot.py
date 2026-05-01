import logging
from telegram import Bot
from src.config import settings

logger = logging.getLogger(__name__)

bot = Bot(token=settings.telegram_bot_token)


async def send_item(title: str, price: str, description: str, location: str, image_url: str, link: str):
    try:
        safe_desc = (description or "")[:300]
        if len(description or "") > 300:
            safe_desc += "..."

        caption = (
            f"*{title}*\n\n"
            f"💰 {price}\n"
            f"📍 {location}\n\n"
            f"{safe_desc}\n\n"
            f"[Ver en Facebook]({link})"
        )

        # Si no hay imagen, enviar como mensaje de texto
        if image_url:
            await bot.send_photo(
                chat_id=settings.telegram_chat_id,
                photo=image_url,
                caption=caption,
                parse_mode="Markdown"
            )
        else:
            await bot.send_message(
                chat_id=settings.telegram_chat_id,
                text=caption,
                parse_mode="Markdown"
            )
        logger.info(f"Item enviado a Telegram: {title}")
    except Exception as e:
        logger.error(f"Error enviando a Telegram: {e}")
