"""
Price Tracker - So sanh gia FPT Shop (baseline) voi doi thu.
Ghép cặp chặt theo dong_may + ram + rom (không dùng LLM cho matching chính).
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

BASELINE_STORE = "FPT Shop"
DATA_FILE = Path(__file__).parent / "mobile_data.json"
OUTPUT_FILE = Path(__file__).parent / "comparison_result.json"


def load_mobile_data(filepath: Path) -> list[dict[str, Any]]:
    if not filepath.exists():
        raise FileNotFoundError(f"Khong tim thay file du lieu: {filepath}")

    with filepath.open(encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("mobile_data.json phai la mot mang JSON.")

    return data


def normalize_storage(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", "", str(value).upper())
    if not text:
        return None
    if text.isdigit():
        return f"{text}GB"
    return text


def normalize_dong_may(name: str) -> str:
    text = name.lower().strip()
    text = re.sub(
        r"\b(5g|4g|nfc|wifi|chính hãng|chinh hang|vn/a|vna|apple việt nam|apple viet nam)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text


def format_sku_label(product: dict[str, Any]) -> str:
    parts = [product["dong_may"]]
    if product.get("ram"):
        parts.append(f"{product['ram']}/{product['rom']}")
    else:
        parts.append(product["rom"])
    if product.get("mau_sac"):
        parts.append(f"({product['mau_sac']})")
    return " ".join(parts)


def build_match_key(product: dict[str, Any]) -> tuple[str, str | None, str]:
    return (
        normalize_dong_may(product["dong_may"]),
        normalize_storage(product.get("ram")),
        normalize_storage(product["rom"]),
    )


def split_baseline_and_competitors(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    baseline: list[dict[str, Any]] = []
    competitors: list[dict[str, Any]] = []

    for item in records:
        store = str(item.get("ten_cua_hang", "")).strip()
        if not item.get("dong_may") or not item.get("rom") or not item.get("gia_ban"):
            continue

        normalized_item = {
            "dong_may": str(item["dong_may"]).strip(),
            "ram": normalize_storage(item.get("ram")),
            "rom": normalize_storage(item["rom"]),
            "mau_sac": item.get("mau_sac"),
            "gia_ban": int(item["gia_ban"]),
            "ten_cua_hang": store,
        }

        if store == BASELINE_STORE:
            baseline.append(normalized_item)
        elif store:
            competitors.append(normalized_item)

    if not baseline:
        raise ValueError(f"Khong co san pham baseline '{BASELINE_STORE}'.")

    if not competitors:
        raise ValueError("Khong co du lieu doi thu de so sanh.")

    return baseline, competitors


def build_competitor_index(
    competitors: list[dict[str, Any]],
) -> dict[tuple[str, str | None, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str | None, str], list[dict[str, Any]]] = defaultdict(list)

    for product in competitors:
        index[build_match_key(product)].append(product)

    return index


def match_products(
    baseline: list[dict[str, Any]],
    competitors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    index = build_competitor_index(competitors)
    results: list[dict[str, Any]] = []

    for fpt_product in baseline:
        key = build_match_key(fpt_product)
        matched_competitors = index.get(key, [])

        if not matched_competitors:
            continue

        for competitor in matched_competitors:
            fpt_price = int(fpt_product["gia_ban"])
            competitor_price = int(competitor["gia_ban"])

            results.append(
                {
                    "Tên SKU FPT Shop": format_sku_label(fpt_product),
                    "Giá FPT Shop": fpt_price,
                    "dong_may": fpt_product["dong_may"],
                    "ram": fpt_product.get("ram"),
                    "rom": fpt_product["rom"],
                    "mau_sac_fpt": fpt_product.get("mau_sac"),
                    "Tên Đối thủ": competitor["ten_cua_hang"],
                    "SKU Đối thủ": format_sku_label(competitor),
                    "Giá Đối thủ": competitor_price,
                    "mau_sac_doi_thu": competitor.get("mau_sac"),
                    "Chênh lệch": competitor_price - fpt_price,
                    "LLM Confident (%)": 100.0,
                    "match_type": "exact_dong_may_ram_rom",
                }
            )

    return results


def save_results(rows: list[dict[str, Any]], filepath: Path) -> None:
    with filepath.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def main() -> int:
    try:
        records = load_mobile_data(DATA_FILE)
        baseline, competitors = split_baseline_and_competitors(records)
        results = match_products(baseline, competitors)
        save_results(results, OUTPUT_FILE)

        print(f"FPT baseline: {len(baseline)} SKU")
        print(f"Doi thu: {len(competitors)} SKU")
        print(f"Ghep cap thanh cong: {len(results)} dong")
        print(f"Ket qua luu tai: {OUTPUT_FILE}")
        return 0

    except FileNotFoundError as exc:
        print(f"[Loi] {exc}", file=sys.stderr)
    except json.JSONDecodeError as exc:
        print(f"[Loi] JSON khong hop le: {exc}", file=sys.stderr)
    except ValueError as exc:
        print(f"[Loi] {exc}", file=sys.stderr)
    except Exception as exc:
        print(f"[Loi] Khong the hoan thanh so sanh gia: {exc}", file=sys.stderr)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
