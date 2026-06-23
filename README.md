# ai-novel-pipeline-demo

A small, runnable Python pipeline that produces website-ready short novels:

```
draft (Grok, Venice backup)  ->  tag + categorize (Claude)  ->  publish (structured web record)
```

It mirrors a real production setup: an LLM writes the story from a topic and
style brief, a second model assigns a controlled-vocabulary category, tags, a
content rating, and a blurb, and the final stage emits a clean JSON record that
a CMS or static-site generator can drop straight onto a website.

> Built as a working demonstration for an Upwork "AI Content Writer for short
> novels" engagement. It runs end to end with **no API keys** thanks to a DEMO
> fallback, so the output shape is visible immediately.

## Architecture

| Stage | File | What it does | Provider |
|-------|------|--------------|----------|
| 1. Draft | `pipeline/generate.py` | Writes the novel from topic + genre + style. Tries Grok, falls back to Venice, then DEMO. | Grok / Venice (OpenAI-compatible) |
| 2. Tag | `pipeline/tag.py` | Forces a JSON classification: one category, 3-6 tags, content rating, blurb. Validates against a closed vocabulary. | Claude (Anthropic Messages) |
| 3. Publish | `pipeline/publish.py` | Slug, id, word count, reading time, URL path; writes `output/<slug>.json`. | local |
| Runner | `run.py` | Wires the three stages together with progress logging. | - |

The drafting client is provider-agnostic because Grok and Venice both expose an
OpenAI-compatible Chat Completions endpoint, so the backup switch is a one-line
provider change. Each stage degrades gracefully: a failed provider falls through
to the next, and a missing key falls through to a deterministic local stub.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Optional - without these, the pipeline runs in DEMO mode:
export GROK_API_KEY=...        # drafting (primary)
export VENICE_API_KEY=...      # drafting (backup)
export ANTHROPIC_API_KEY=...   # tagging / categorization
```

No secrets are committed to this repo. Keys are read from the environment only.

## Run

```bash
python run.py --topic "a forgotten lighthouse" --genre Adventure --words 1200
# force the backup provider:
python run.py --topic "a heist on Mars" --genre "Science Fiction" --provider venice
```

Output (a website-ready record) lands in `output/<slug>.json`:

```json
{
  "id": "a1b2c3d4e5f6",
  "slug": "the-lighthouse-at-dusk",
  "title": "The Lighthouse at Dusk",
  "category": "Adventure",
  "tags": ["harbor", "keeper", "choice", "water"],
  "content_rating": "general",
  "blurb": "A keeper opens a door that will not close behind her.",
  "word_count": 1187,
  "reading_minutes": 5,
  "url_path": "/novels/adventure/the-lighthouse-at-dusk",
  "body": "...",
  "pipeline": { "drafted_by": "grok", "tagged_by": "claude", "generated_at": "..." }
}
```

## Extending for a real site

- Swap `publish()` to POST the record to your CMS API (WordPress, Strapi, Sanity)
  instead of writing a file.
- Drive topics/styles from a CSV or a sheet to batch-generate a backlog.
- Add a dedup/quality gate between stages 1 and 2 (length, banned-content check).
