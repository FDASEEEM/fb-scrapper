from upstash_redis import Redis
from src.config import settings

redis = Redis(
    url=settings.upstash_redis_rest_url,
    token=settings.upstash_redis_rest_token
)

PROCESSED_SET = "fb_marketplace:processed_ids"


def is_processed(item_id: str) -> bool:
    return bool(redis.sismember(PROCESSED_SET, item_id))


def mark_processed(item_id: str):
    redis.sadd(PROCESSED_SET, item_id)
