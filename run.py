#!/usr/bin/env python3
"""
End-to-end runner for the AI short-novel pipeline.

    draft (Grok / Venice backup)  ->  tag (Claude)  ->  publish (web record)

Runs fully offline in DEMO mode when no API keys are set, so you can see the
exact output shape without any credentials.

Usage:
    python run.py --topic "a lighthouse" --genre Adventure --words 1200
    python run.py --topic "a lighthouse" --genre Adventure --provider venice
"""

from __future__ import annotations

import argparse
import json

from pipeline.generate import NovelBrief, generate_novel
from pipeline.tag import tag_novel
from pipeline.publish import build_record, publish


def main() -> None:
    parser = argparse.ArgumentParser(description="AI short-novel pipeline")
    parser.add_argument("--topic", default="a forgotten lighthouse")
    parser.add_argument("--genre", default="Adventure")
    parser.add_argument("--words", type=int, default=1200)
    parser.add_argument("--style", default="tight prose, vivid sensory detail, a clear arc")
    parser.add_argument("--provider", default="grok", choices=["grok", "venice"])
    parser.add_argument("--out", default="output")
    args = parser.parse_args()

    brief = NovelBrief(
        topic=args.topic,
        genre=args.genre,
        target_words=args.words,
        style_notes=args.style,
    )

    print(f"[1/3] Drafting via {args.provider} (backup + demo fallback enabled) ...")
    draft = generate_novel(brief, provider=args.provider)
    print(f"      title: {draft['title']!r}  (drafted_by={draft['provider_used']})")

    print("[2/3] Tagging / categorizing via Claude ...")
    tags = tag_novel(draft["title"], draft["body"])
    print(f"      category={tags['category']}  tags={tags['tags']}  (tagged_by={tags['tagger_used']})")

    print("[3/3] Building website record + writing JSON ...")
    record = build_record(draft, tags)
    path = publish(record, out_dir=args.out)
    print(f"      wrote {path}")

    print("\n--- structured record (preview) ---")
    preview = {k: v for k, v in record.items() if k != "body"}
    print(json.dumps(preview, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
