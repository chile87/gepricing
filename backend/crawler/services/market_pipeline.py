from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

from crawlPrice.crawl_mobile import OUTPUT_FILE, main as crawl_mobile_main

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def collect_mobile_market_data(output_path: str | None = None) -> dict[str, Any]:
    target_file = Path(output_path) if output_path else OUTPUT_FILE
    crawl_mode = "cached"

    if os.getenv("FIRECRAWL_API_KEY"):
        crawl_mobile_main()
        crawl_mode = "firecrawl"
    elif not target_file.exists():
        raise RuntimeError("mobile_data.json not found and FIRECRAWL_API_KEY is not configured")

    enrichment = maybe_normalize_with_gemini(target_file)
    return {
        "outputFile": str(target_file),
        "crawlMode": crawl_mode,
        **enrichment,
    }


def maybe_normalize_with_gemini(file_path: Path) -> dict[str, Any]:
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"semanticMatching": "skipped", "normalizedRows": 0}

    rows = json.loads(file_path.read_text(encoding="utf-8"))
    if not rows:
        return {"semanticMatching": "skipped", "normalizedRows": 0}

    normalized = _normalize_rows_with_gemini(rows, api_key)
    if not normalized:
        return {"semanticMatching": "fallback", "normalizedRows": 0}

    file_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"semanticMatching": "gemini", "normalizedRows": len(normalized)}


def _normalize_rows_with_gemini(rows: list[dict[str, Any]], api_key: str) -> list[dict[str, Any]]:
    prompt = {
        "instruction": (
            "Normalize Vietnamese mobile phone listings into a consistent schema. "
            "Keep one object per input row. Preserve store names and prices. "
            "Canonicalize dong_may, ram, rom, mau_sac where possible."
        ),
        "schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dong_may": {"type": "string"},
                    "ram": {"type": ["string", "null"]},
                    "rom": {"type": ["string", "null"]},
                    "mau_sac": {"type": ["string", "null"]},
                    "gia_ban": {"type": "integer"},
                    "ten_cua_hang": {"type": "string"},
                },
                "required": ["dong_may", "gia_ban", "ten_cua_hang"],
            },
        },
        "rows": rows[:200],
    }

    response = requests.post(
        f"{GEMINI_BASE_URL}/{GEMINI_MODEL}:generateContent?key={api_key}",
        json={
            "contents": [
                {
                    "parts": [
                        {
                            "text": json.dumps(prompt, ensure_ascii=False),
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
            },
        },
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()
    text_output = (
        body.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "")
    )
    parsed = json.loads(text_output)
    return [row for row in parsed if isinstance(row, dict)]
