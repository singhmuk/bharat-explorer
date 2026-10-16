"""
Application-layer anti-scraping. This is the LAST line of defence:
put Cloudflare/AWS WAF (bot management) in front, and use these as backup.

Layers:
 1. Known AI/scraper user-agents are refused.
 2. Missing/odd headers on API calls are refused.
 3. Per-IP rate limit (Redis).
 4. Crawl-pattern detector: too many DISTINCT destination pages per minute -> ban.
 5. Honeypot URL (disallowed in robots.txt, hidden link) -> ban.
"""
import re
import redis
from fastapi import Request
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .config import settings

r = redis.Redis.from_url(settings.redis_url, decode_responses=True)

BLOCKED_UA = re.compile(
    r"(gptbot|chatgpt-user|oai-searchbot|claudebot|claude-web|anthropic-ai|ccbot|perplexity|"
    r"bytespider|google-extended|amazonbot|applebot-extended|cohere|diffbot|imagesift|omgili|"
    r"meta-externalagent|facebookbot|petalbot|ai2bot|timpibot|youbot|scrapy|python-requests|"
    r"aiohttp|httpx|go-http-client|curl|wget|libwww|okhttp|headless|phantomjs|selenium|puppeteer|playwright)",
    re.I,
)
PUBLIC_PREFIXES = ("/health", "/metrics", "/robots.txt")
HONEYPOT = "/api/internal/sitemap-full"

ROBOTS = """User-agent: *
Disallow: /api/
Disallow: /api/internal/

User-agent: GPTBot
Disallow: /
User-agent: ClaudeBot
Disallow: /
User-agent: anthropic-ai
Disallow: /
User-agent: CCBot
Disallow: /
User-agent: Google-Extended
Disallow: /
User-agent: PerplexityBot
Disallow: /
User-agent: Bytespider
Disallow: /
User-agent: Amazonbot
Disallow: /
"""


def client_ip(request: Request) -> str:
    # --proxy-headers makes uvicorn trust X-Forwarded-For; restrict to your ingress in prod.
    return request.client.host if request.client else "unknown"


def deny(msg="Automated access is not permitted", code=403):
    return JSONResponse({"detail": msg}, status_code=code)


class BotShield(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path == "/robots.txt":
            return PlainTextResponse(ROBOTS)
        if path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)

        ip = client_ip(request)
        try:
            if r.exists(f"ban:{ip}"):
                return deny("Temporarily blocked", 429)

            if path.startswith(HONEYPOT):
                r.setex(f"ban:{ip}", settings.ban_seconds * 24, 1)
                return deny()

            ua = request.headers.get("user-agent", "")
            if not ua or BLOCKED_UA.search(ua):
                r.setex(f"ban:{ip}", settings.ban_seconds, 1)
                return deny()

            if request.headers.get("x-requested-with") != "bharat-web":
                return deny()  # our React app always sends this header

            key = f"rl:{ip}:{request.scope.get('time', 0) or ''}"
            pipe = r.pipeline()
            bucket = f"rl:{ip}"
            pipe.incr(bucket)
            pipe.expire(bucket, 60, nx=True)
            count, _ = pipe.execute()
            if count > settings.rate_limit_per_minute:
                return deny("Too many requests", 429)

            if path.startswith("/api/destinations/") and request.method == "GET":
                slug = path.rsplit("/", 1)[-1]
                k = f"crawl:{ip}"
                pipe = r.pipeline()
                pipe.sadd(k, slug)
                pipe.expire(k, 60, nx=True)
                pipe.scard(k)
                _, _, distinct = pipe.execute()
                if distinct > settings.max_distinct_pages_per_minute:
                    r.setex(f"ban:{ip}", settings.ban_seconds, 1)
                    return deny("Temporarily blocked", 429)
        except redis.RedisError:
            pass  # fail open on Redis outage; WAF is still in front

        resp = await call_next(request)
        resp.headers["X-Robots-Tag"] = "noai, noimageai, noindex"
        return resp
