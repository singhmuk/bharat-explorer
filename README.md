# Bharat Explorer

India travel-discovery site. React + TypeScript (Vite), FastAPI, MySQL, Redis, Celery, Claude API, Docker, Kubernetes, Prometheus/Grafana.

## Run locally
    cp .env.example .env     # add ANTHROPIC_API_KEY
    docker compose up --build
    # site: http://localhost:8080   Prometheus: :9090   Grafana: :3000

## How it works
- Every view / save / affiliate click is stored in `visits`. A Celery task rebuilds the user's
  recommendations (tag affinity with 30-day decay) and caches them in Redis.
- `/api/ai/itinerary` queues a Celery job that calls the LLM with the user's top interests plus your destination catalog. The UI polls for the result.

## Earning money
1. Affiliate stays/tours (Booking, Agoda, MakeMyTrip, Viator, GetYourGuide): set `affiliate_url` per destination. Clicks go through `/api/go/{slug}`, so you can attribute revenue.
2. Display ads: AdSense slots in `AdSlot.tsx` (needs approval and a cookie-consent banner for GDPR/DPDP).
3. Premium plan: free users get 2 AI itineraries/day; add Razorpay/Stripe checkout to flip `is_premium`.
4. Later: sponsored listings from hotels and tour operators (label them "Sponsored").

## Blocking AI scrapers (layered; no method is 100%)
1. **CDN/WAF (most important):** Cloudflare "Block AI Bots" + Bot Fight/Super Bot Fight, or AWS WAF Bot Control.
2. `robots.txt` + `X-Robots-Tag: noai` (polite crawlers obey; bad ones ignore).
3. nginx user-agent blocklist and rate limit (`frontend/nginx.conf`).
4. `BotShield` middleware: UA block, required `X-Requested-With`, Redis rate limit, crawl-pattern ban, honeypot link.
5. API returns max 12 items per page; no bulk-export endpoint; login required for AI and tracking.
6. Add Cloudflare Turnstile to login/register. Consider watermarking text and monitoring logs for abuse.
Determined scrapers using real browsers and rotating IPs can still copy publicly visible pages. Anything a human can read, a bot can eventually read; the goal is to make it costly.

## Before production
- Replace `create_all` with Alembic migrations; use managed MySQL; seal secrets.
- Trust `X-Forwarded-For` only from your ingress; add HTTPS, CSP headers.
- Add privacy policy, affiliate disclosure and cookie consent (India DPDP Act).
- Add Grafana dashboards: API p95 latency, 5xx rate, Celery queue length, blocked-request counter.
