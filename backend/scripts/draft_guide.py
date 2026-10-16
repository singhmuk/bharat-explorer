"""
Draft a first version of a place guide with your local Ollama model.
    cd backend && python -m scripts.draft_guide munnar
Output goes to app/content/drafts/<slug>.md. It is NOT published.
Rewrite it, fact-check prices/timings/distances, add your own experience,
then move it to app/content/<slug>.md and restart the API.
Unedited AI text ranks badly and often contains wrong facts.
"""
import os
import sys
from pathlib import Path

import httpx

from app.seed import DATA

OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("LLM_MODEL", "llama3.2")

PROMPT = """Write a practical travel guide (about 900 words, Markdown, ## headings) for {name}, {state}, India.
Sections: intro, Best time to visit, How to reach (air, train, road), Getting around, Top things to see,
What to eat, Where to stay (areas, not hotel names), Indicative costs, a 3-day itinerary, Practical tips.
Rules: do not invent exact prices, timings or ticket fees; use ranges and say 'check current rates'.
Do not mention anything you are unsure of. Known facts: {summary} {desc} Best season: {season}."""


def main(slug: str):
    row = next((r for r in DATA if r[0] == slug), None)
    if not row:
        sys.exit(f"Unknown slug. Choose from: {', '.join(r[0] for r in DATA)}")
    _, name, state, _, summary, desc, season, *_ = row
    r = httpx.post(f"{OLLAMA}/api/chat", timeout=600, json={
        "model": MODEL, "stream": False, "options": {"num_predict": 2000},
        "messages": [{"role": "user", "content": PROMPT.format(
            name=name, state=state, summary=summary, desc=desc, season=season)}]})
    r.raise_for_status()
    out = Path(__file__).resolve().parent.parent / "app" / "content" / "drafts"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{slug}.md").write_text(
        f"title: {name} travel guide: best time, how to reach, itinerary | Bharat Explorer\n"
        f"description: Plan {name}, {state}: best months, how to get there, where to stay, costs and an itinerary.\n---\n"
        + r.json()["message"]["content"], encoding="utf-8")
    print("Draft saved:", out / f"{slug}.md")


if __name__ == "__main__":
    main(sys.argv[1])
