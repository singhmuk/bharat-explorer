from datetime import datetime
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from celery.result import AsyncResult
from .db import get_db
from .models import User, Destination, Visit
from .schemas import (Credentials, Token, DestinationOut, DestinationDetail, VisitIn, ItineraryIn)
from .security import hash_password, verify_password, make_token, current_user
from .tasks import celery, refresh_recommendations, generate_itinerary, rds
from .config import settings
from .recommender import recommend

router = APIRouter(prefix="/api")


@router.post("/auth/register", response_model=Token)
def register(body: Credentials, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(409, "This email is already registered")
    u = User(email=body.email, password_hash=hash_password(body.password))
    db.add(u); db.commit()
    return Token(access_token=make_token(u.id))


@router.post("/auth/login", response_model=Token)
def login(body: Credentials, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.email == body.email))
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Email or password is incorrect")
    return Token(access_token=make_token(u.id), is_premium=u.is_premium)


@router.get("/destinations", response_model=list[DestinationOut])
def list_destinations(region: str | None = None, tag: str | None = None,
                      q: str | None = Query(None, max_length=60),
                      page: int = Query(1, ge=1), db: Session = Depends(get_db)):
    stmt = select(Destination).order_by(Destination.popularity.desc())
    if region: stmt = stmt.where(Destination.region == region)
    if q: stmt = stmt.where(Destination.name.like(f"%{q}%"))
    rows = db.scalars(stmt).all()
    if tag: rows = [d for d in rows if tag in (d.tags or [])]
    return rows[(page - 1) * 12: page * 12]  # hard page size: no bulk dumps


@router.get("/destinations/{slug}", response_model=DestinationDetail)
def destination(slug: str, db: Session = Depends(get_db)):
    d = db.scalar(select(Destination).where(Destination.slug == slug))
    if not d: raise HTTPException(404, "Destination not found")
    return d


@router.post("/visits", status_code=202)
def track(body: VisitIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    d = db.scalar(select(Destination).where(Destination.slug == body.slug))
    if not d: raise HTTPException(404, "Destination not found")
    db.add(Visit(user_id=user.id, destination_id=d.id, action=body.action))
    db.execute(update(Destination).where(Destination.id == d.id).values(popularity=Destination.popularity + 1))
    db.commit()
    refresh_recommendations.delay(user.id)
    return {"ok": True}


@router.get("/go/{slug}")
def affiliate(slug: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Returns the affiliate URL and records the click (revenue attribution)."""
    d = db.scalar(select(Destination).where(Destination.slug == slug))
    if not d or not d.affiliate_url: raise HTTPException(404, "No booking link for this place yet")
    db.add(Visit(user_id=user.id, destination_id=d.id, action="affiliate_click")); db.commit()
    return {"url": d.affiliate_url}


@router.get("/recommendations")
def recommendations(user: User = Depends(current_user), db: Session = Depends(get_db)):
    cached = rds.get(f"recs:{user.id}")
    return json.loads(cached) if cached else recommend(db, user)


@router.put("/me/interests")
def set_interests(interests: list[str], user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.interests = [i[:30] for i in interests[:10]]; db.commit()
    refresh_recommendations.delay(user.id)
    return {"ok": True}


@router.post("/ai/itinerary", status_code=202)
def itinerary(body: ItineraryIn, user: User = Depends(current_user)):
    if not user.is_premium:  # monetisation: free tier quota
        key = f"quota:{user.id}:{datetime.utcnow():%Y%m%d}"
        n = rds.incr(key); rds.expire(key, 86400)
        if n > settings.free_itineraries_per_day:
            raise HTTPException(402, "Free plan allows 2 itineraries a day. Upgrade for unlimited plans")
    task = generate_itinerary.delay(user.id, body.prompt, body.days)
    return {"task_id": task.id}


@router.get("/ai/itinerary/{task_id}")
def itinerary_result(task_id: str, user: User = Depends(current_user)):
    res = AsyncResult(task_id, app=celery)
    if res.state == "SUCCESS": return {"status": "done", "text": res.result}
    if res.state == "FAILURE": return {"status": "failed"}
    return {"status": "pending"}
