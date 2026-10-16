"""Content-based recommender: learns tag affinity from the user's behaviour."""
from collections import Counter
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Visit, Destination, User

WEIGHT = {"view": 1.0, "save": 3.0, "affiliate_click": 4.0}


def tag_profile(db: Session, user: User) -> Counter:
    prof: Counter = Counter({t: 2.0 for t in (user.interests or [])})
    rows = db.execute(
        select(Visit, Destination).join(Destination, Destination.id == Visit.destination_id)
        .where(Visit.user_id == user.id).order_by(Visit.created_at.desc()).limit(300)
    ).all()
    now = datetime.utcnow()
    for v, d in rows:
        decay = 0.5 ** ((now - v.created_at).days / 30)  # half-life 30 days
        for t in d.tags or []:
            prof[t] += WEIGHT.get(v.action, 1) * decay
    return prof


def recommend(db: Session, user: User, limit: int = 6) -> list[dict]:
    prof = tag_profile(db, user)
    seen = {x for (x,) in db.execute(select(Visit.destination_id).where(
        Visit.user_id == user.id, Visit.action.in_(["save", "affiliate_click"])))}
    dests = db.scalars(select(Destination)).all()
    max_pop = max((d.popularity for d in dests), default=1) or 1
    scored = []
    for d in dests:
        if d.id in seen:
            continue
        overlap = [t for t in d.tags if prof.get(t)]
        score = sum(prof[t] for t in overlap) + 0.5 * d.popularity / max_pop
        reason = f"Because you like {', '.join(overlap[:2])}" if overlap else "Popular with travellers"
        scored.append((score, d, reason))
    scored.sort(key=lambda x: -x[0])
    return [{"slug": d.slug, "name": d.name, "state": d.state, "summary": d.summary,
             "tags": d.tags, "reason": reason} for _, d, reason in scored[:limit]]
