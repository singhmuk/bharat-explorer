from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    interests: Mapped[list] = mapped_column(JSON, default=list)  # explicit preferences
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Destination(Base):
    __tablename__ = "destinations"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    state: Mapped[str] = mapped_column(String(80), index=True)
    region: Mapped[str] = mapped_column(String(40))  # North, South, East, West, Central, Northeast
    summary: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    best_season: Mapped[str] = mapped_column(String(80))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    tags: Mapped[list] = mapped_column(JSON, default=list)  # e.g. ["mountain","trek","spiritual"]
    affiliate_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    popularity: Mapped[int] = mapped_column(Integer, default=0)


class Visit(Base):
    """Every interaction: view, save, affiliate_click."""
    __tablename__ = "visits"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id"), index=True)
    action: Mapped[str] = mapped_column(String(20), default="view")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (Index("ix_visits_user_time", "user_id", "created_at"),)
