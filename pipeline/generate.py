"""
Drafting stage.

Generates a short novel from a topic + style brief using an LLM (Grok by
default; Venice as a backup provider). Both providers expose an
OpenAI-compatible Chat Completions endpoint, so a single client works for both.

If no API key is configured, the module runs in DEMO mode and returns a
deterministic local draft so the whole pipeline is runnable with zero secrets.
"""

from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass

import requests


# OpenAI-compatible endpoints. Grok = x.ai, Venice = venice.ai.
PROVIDERS = {
    "grok": {
        "base_url": "https://api.x.ai/v1/chat/completions",
        "model": os.getenv("GROK_MODEL", "grok-2-latest"),
        "key_env": "GROK_API_KEY",
    },
    "venice": {
        "base_url": "https://api.venice.ai/api/v1/chat/completions",
        "model": os.getenv("VENICE_MODEL", "llama-3.3-70b"),
        "key_env": "VENICE_API_KEY",
    },
}


@dataclass
class NovelBrief:
    topic: str
    genre: str
    target_words: int = 1200
    style_notes: str = "tight prose, vivid sensory detail, a clear arc"


def _build_prompt(brief: NovelBrief) -> str:
    return textwrap.dedent(
        f"""
        Write a complete short novel of about {brief.target_words} words.

        Topic: {brief.topic}
        Genre: {brief.genre}
        Style: {brief.style_notes}

        Requirements:
        - A clear beginning, middle, and end with a satisfying resolution.
        - A title on the first line, prefixed with "TITLE: ".
        - No meta commentary, no notes to the reader, only the story.
        """
    ).strip()


def _call_llm(provider: str, prompt: str, timeout: int = 90) -> str:
    cfg = PROVIDERS[provider]
    key = os.getenv(cfg["key_env"])
    if not key:
        raise RuntimeError(f"no API key in env var {cfg['key_env']}")
    resp = requests.post(
        cfg["base_url"],
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": cfg["model"],
            "messages": [
                {"role": "system", "content": "You are a skilled novelist."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.9,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _demo_draft(brief: NovelBrief) -> str:
    """Deterministic offline draft so the pipeline runs without any key."""
    return textwrap.dedent(
        f"""
        TITLE: The {brief.topic.title()} at Dusk

        The harbor went quiet the evening everything changed. Mara had spent
        years circling the same {brief.topic}, the way a moth circles a lamp it
        cannot name, and on this night the circling finally stopped.

        She had been warned. The old keeper told her that some doors, once
        opened, do not close behind you. She opened it anyway, because curiosity
        is only ever a polite word for hunger.

        What she found on the other side was not what she feared. It was smaller,
        and truer, and it asked only one thing of her: that she choose, plainly,
        and live with the choosing.

        She chose. The lamp guttered. The harbor breathed again, and Mara walked
        home along the water with the strange, light feeling of a person who has
        finally set something down.

        (Genre: {brief.genre}. Style: {brief.style_notes}.)
        """
    ).strip()


def generate_novel(brief: NovelBrief, provider: str = "grok") -> dict:
    """
    Draft a novel. Tries `provider`, falls back to the other configured
    provider, then to DEMO mode. Returns {title, body, provider_used}.
    """
    order = [provider] + [p for p in PROVIDERS if p != provider]
    last_err = None
    for prov in order:
        try:
            text = _call_llm(prov, _build_prompt(brief))
            return _split(text, provider_used=prov)
        except Exception as exc:  # noqa: BLE001 - backup is the whole point
            last_err = exc
            continue
    text = _demo_draft(brief)
    return _split(text, provider_used="demo")


def _split(text: str, provider_used: str) -> dict:
    title = "Untitled"
    body = text
    first, _, rest = text.partition("\n")
    if first.upper().startswith("TITLE:"):
        title = first.split(":", 1)[1].strip()
        body = rest.strip()
    return {"title": title, "body": body, "provider_used": provider_used}
