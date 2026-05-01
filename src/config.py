from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Facebook
    fb_email: str = Field(..., alias="FB_EMAIL")
    fb_password: str = Field(..., alias="FB_PASSWORD")

    # Telegram
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(..., alias="TELEGRAM_CHAT_ID")

    # Redis
    upstash_redis_rest_url: str = Field(..., alias="UPSTASH_REDIS_REST_URL")
    upstash_redis_rest_token: str = Field(..., alias="UPSTASH_REDIS_REST_TOKEN")

    # Search
    search_keywords: str = Field(default="", alias="SEARCH_KEYWORDS")
    search_categories: str = Field(default="", alias="SEARCH_CATEGORIES")
    marketplace_cities: str = Field(default="vina-del-mar,valparaiso", alias="MARKETPLACE_CITIES")
    search_radius_km: int = Field(default=30, alias="SEARCH_RADIUS_KM")
    check_interval_minutes: int = Field(default=60, alias="CHECK_INTERVAL_MINUTES")
    headless: bool = Field(default=True, alias="HEADLESS")
    max_items_per_search: int = Field(default=20, alias="MAX_ITEMS_PER_SEARCH")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
