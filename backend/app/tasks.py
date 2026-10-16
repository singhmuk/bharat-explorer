import json
import anthropic
from celery import Celery
from .config import settings
from .db import SessionLocal
from .models import User, Destination
from . import recommender
import redis

celery = Celery("bharat", broker=settings.redis_url, backend=settings.redis_url)
celery.conf.update(task_serializer="json", result_expires=3600, task_acks_late=True,
                   worker_prefetch_multiplier=1)
rds = redis.Redis.from_url(settings.redis_url, decode_responses=True)


@celery.task
def refresh_recommendations(user_id: int):
    """Triggered after each visit; result cached in Redis for the dashboard."""
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user:
            rds.setex(f"recs:{user_id}", 3600, json.dumps(recommender.recommend(db, user)))


@celery.task(bind=True, autoretry_for=(anthropic.APIError,), retry_backoff=True, max_retries=2)
def generate_itinerary(self, user_id: int, prompt: str, days: int):
    with SessionLocal() as db:
        user = db.get(User, user_id)
        prof = recommender.tag_profile(db, user)
        catalog = [f"{d.name} ({d.state}; {', '.join(d.tags)}; best {d.best_season})"
                   for d in db.query(Destination).all()]
    top = ", ".join(t for t, _ in prof.most_common(5)) or "none yet"
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model=settings.llm_model,
        max_tokens=1800,
        system=("You are a travel planner for India. Build a realistic day-by-day itinerary. "
                "Prefer places from the catalog but you may add nearby stops. Mention best season, "
                "travel time between stops and one local food tip per day. Be concise. Use Markdown."),
        messages=[{"role": "user", "content":
                   f"Trip request: {prompt}\nDays: {days}\nUser interests: {top}\n"
                   f"Catalog:\n- " + "\n- ".join(catalog)}],
    )
    return msg.content[0].text
