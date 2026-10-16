"""
Server-rendered HTML for search engines (and for humans: React takes over after load).
nginx sends  /  and  /place/<slug>  here. We take the built React index.html ("shell"),
inject <title>, meta tags, JSON-LD and the full article text, and return it.
"""
import html
import json
import os
import re
import time

import httpx
import markdown
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Destination

router = APIRouter()
SITE = os.getenv("SITE_URL", "http://localhost:8080").rstrip("/")
WEB = os.getenv("WEB_URL", "http://web")
esc = html.escape

DEV_SHELL = ('<!doctype html><html lang="en"><head><meta charset="UTF-8"/>'
             '<meta name="viewport" content="width=device-width, initial-scale=1"/><title></title></head>'
             '<body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>')
_shell = {"t": 0.0, "html": DEV_SHELL}


def get_shell() -> str:
    if time.time() - _shell["t"] > 300:
        try:
            r = httpx.get(f"{WEB}/__shell.html", timeout=3, headers={"User-Agent": "BharatSSR/1.0"})
            r.raise_for_status()
            _shell.update(t=time.time(), html=r.text)
        except httpx.HTTPError:
            _shell["t"] = time.time() - 240  # retry in about a minute
    return _shell["html"]


def render(title: str, head: str, body: str, status: int = 200) -> HTMLResponse:
    doc = get_shell()
    doc = re.sub(r"<title>.*?</title>", "", doc, flags=re.S)
    doc = re.sub(r'<meta name="robots"[^>]*>', "", doc)
    doc = doc.replace("</head>", f"<title>{esc(title)}</title>{head}</head>", 1)
    doc = doc.replace('<div id="root"></div>', f'<div id="root">{body}</div>', 1)
    return HTMLResponse(doc, status_code=status)


def ld(data: dict) -> str:
    return '<script type="application/ld+json">' + json.dumps(data).replace("</", "<\\/") + "</script>"


@router.get("/ssr/home")
def ssr_home(db: Session = Depends(get_db)):
    title = "Bharat Explorer: India travel guides, itineraries and trip planner"
    desc = ("Detailed travel guides for places across India: best time to visit, how to reach, "
            "where to stay and day-by-day itineraries, plus AI trip planning.")
    dests = db.scalars(select(Destination).order_by(Destination.popularity.desc())).all()
    items = "".join(f'<li><a href="/place/{d.slug}">{esc(d.name)}, {esc(d.state)}</a>: {esc(d.summary)}</li>' for d in dests)
    head = (f'<meta name="description" content="{esc(desc)}"/><link rel="canonical" href="{SITE}/"/>'
            f'<meta name="robots" content="index,follow,max-image-preview:large,noai,noimageai"/>'
            f'<meta property="og:title" content="{esc(title)}"/><meta property="og:description" content="{esc(desc)}"/>'
            f'<meta property="og:type" content="website"/><meta property="og:url" content="{SITE}/"/>')
    return render(title, head, f"<main><h1>Plan your trip across India</h1><p>{esc(desc)}</p><ul>{items}</ul></main>")


@router.get("/ssr/place/{slug}")
def ssr_place(slug: str, db: Session = Depends(get_db)):
    d = db.scalar(select(Destination).where(Destination.slug == slug))
    if not d:
        return render("Place not found | Bharat Explorer", '<meta name="robots" content="noindex"/>',
                      "<main><h1>Place not found</h1><p><a href='/'>Browse all places</a></p></main>", 404)
    title = d.meta_title or f"{d.name}, {d.state}: travel guide, best time and itinerary | Bharat Explorer"
    desc = d.meta_description or d.summary
    url = f"{SITE}/place/{d.slug}"
    img = f"{SITE}{d.image_url}" if d.image_url and d.image_url.startswith("/") else d.image_url
    schema = {"@context": "https://schema.org", "@type": "TouristDestination", "name": d.name,
              "description": desc, "url": url,
              "geo": {"@type": "GeoCoordinates", "latitude": d.lat, "longitude": d.lng},
              "containedInPlace": {"@type": "State", "name": d.state}}
    if img:
        schema["image"] = img
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Places", "item": f"{SITE}/"},
        {"@type": "ListItem", "position": 2, "name": d.name, "item": url}]}
    head = (f'<meta name="description" content="{esc(desc)}"/><link rel="canonical" href="{url}"/>'
            f'<meta name="robots" content="index,follow,max-image-preview:large,noai,noimageai"/>'
            f'<meta property="og:title" content="{esc(title)}"/><meta property="og:description" content="{esc(desc)}"/>'
            f'<meta property="og:type" content="article"/><meta property="og:url" content="{url}"/>'
            + (f'<meta property="og:image" content="{esc(img)}"/>' if img else "")
            + ld(schema) + ld(crumbs))
    # guide_md is written by you (trusted); do not render user-submitted Markdown this way.
    guide = markdown.markdown(d.guide_md or d.description, extensions=["extra"])
    pic = (f'<img src="{esc(d.image_url)}" alt="{esc(d.image_alt or f"{d.name}, {d.state}")}" width="1200" height="675"/>'
           if d.image_url else "")
    others = db.scalars(select(Destination).where(Destination.id != d.id).limit(8)).all()
    more = "".join(f'<li><a href="/place/{o.slug}">{esc(o.name)}</a></li>' for o in others)
    body = (f"<main><p>{esc(d.state)}. Best time: {esc(d.best_season)}</p><h1>{esc(d.name)}</h1>{pic}"
            f"<article>{guide}</article><nav><h2>More places in India</h2><ul>{more}</ul></nav></main>")
    return render(title, head, body)


@router.get("/sitemap.xml")
def sitemap(db: Session = Depends(get_db)):
    rows = db.execute(select(Destination.slug, Destination.updated_at)).all()
    urls = [f"<url><loc>{SITE}/</loc></url>"]
    for slug, ts in rows:
        last = f"<lastmod>{ts:%Y-%m-%d}</lastmod>" if ts else ""
        urls.append(f"<url><loc>{SITE}/place/{esc(slug)}</loc>{last}</url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           + "".join(urls) + "</urlset>")
    return Response(xml, media_type="application/xml")
