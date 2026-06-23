"""
Tagging / categorization stage.

Sends the drafted novel to Claude (Anthropic Messages API) and asks for a
controlled-vocabulary classification: one primary category, a list of tags,
content rating, and a one-line blurb. The model is forced to return JSON.

DEMO mode (no ANTHROPIC_API_KEY) derives tags from a small keyword map so the
pipeline still produces a structured, deterministic record.
"""

from __future__ import annotations

import json
import os
import re

import requests


ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")

# Closed category vocabulary for a website taxonomy.
CATEGORIES = [
    "Fantasy", "Science Fiction", "Mystery", "Romance",
    "Horror", "Literary", "Adventure", "Thriller",
]


def _build_prompt(title: str, body: str) -> str:
    cats = ", ".join(CATEGORIES)
    return (
        "Classify this short novel for a publishing website. "
        f"Choose exactly one primary category from: {cats}. "
        "Return STRICT JSON with keys: category (string from the list), "
        "tags (array of 3-6 lowercase strings), content_rating "
        "(one of 'general','teen','mature'), blurb (one sentence under 30 words). "
        "Return JSON only, no prose.\n\n"
        f"TITLE: {title}\n\nSTORY:\n{body[:6000]}"
    )


def _call_claude(prompt: str, timeout: int = 60) -> dict:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("no ANTHROPIC_API_KEY")
    resp = requests.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    text = resp.json()["content"][0]["text"]
    return _parse_json(text)


def _parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in model output")
    return json.loads(match.group(0))


_KEYWORDS = {
    "Fantasy": ["lamp", "keeper", "door", "spell", "dragon", "magic"],
    "Science Fiction": ["ship", "star", "robot", "future", "orbit"],
    "Mystery": ["clue", "detective", "missing", "secret"],
    "Romance": ["love", "kiss", "heart", "longing"],
    "Horror": ["blood", "dark", "fear", "scream", "shadow"],
    "Adventure": ["harbor", "journey", "map", "water", "voyage"],
}


def _demo_tags(title: str, body: str) -> dict:
    text = (title + " " + body).lower()
    scores = {
        cat: sum(text.count(k) for k in words)
        for cat, words in _KEYWORDS.items()
    }
    category = max(scores, key=scores.get) if any(scores.values()) else "Literary"
    words = re.findall(r"[a-z]{5,}", text)
    common = sorted(set(words), key=lambda w: -text.count(w))[:4] or ["story"]
    return {
        "category": category,
        "tags": common,
        "content_rating": "general",
        "blurb": (body.split(".")[0].strip()[:120] + ".") if body else "A short tale.",
    }


def tag_novel(title: str, body: str) -> dict:
    """Return {category, tags, content_rating, blurb, tagger_used}."""
    try:
        result = _call_claude(_build_prompt(title, body))
        result["tagger_used"] = "claude"
    except Exception:  # noqa: BLE001
        result = _demo_tags(title, body)
        result["tagger_used"] = "demo"
    # Guard against an out-of-vocabulary category.
    if result.get("category") not in CATEGORIES:
        result["category"] = "Literary"
    return result
