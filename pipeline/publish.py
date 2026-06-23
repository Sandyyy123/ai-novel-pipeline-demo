"""
Publish stage.

Assembles a structured, website-ready record (the kind of JSON a CMS or a
static-site generator can consume) from the draft and the tags, then writes it
to the output directory. A URL slug is derived from the title.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "untitled"


def build_record(draft: dict, tags: dict) -> dict:
    title = draft["title"]
    body = draft["body"]
    slug = _slugify(title)
    novel_id = hashlib.sha1((slug + body[:200]).encode()).hexdigest()[:12]
    word_count = len(body.split())
    return {
        "id": novel_id,
        "slug": slug,
        "title": title,
        "category": tags["category"],
        "tags": tags["tags"],
        "content_rating": tags["content_rating"],
        "blurb": tags["blurb"],
        "word_count": word_count,
        "reading_minutes": max(1, round(word_count / 220)),
        "body": body,
        "url_path": f"/novels/{tags['category'].lower().replace(' ', '-')}/{slug}",
        "pipeline": {
            "drafted_by": draft["provider_used"],
            "tagged_by": tags["tagger_used"],
            "generated_at": _dt.datetime.utcnow().isoformat() + "Z",
        },
    }


def publish(record: dict, out_dir: str = "output") -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{record['slug']}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)
    return path
