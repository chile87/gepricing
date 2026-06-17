"""Export mobile_data.json and comparison_result.json to Excel."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent
MOBILE_FILE = BASE_DIR / "mobile_data.json"
COMPARISON_FILE = BASE_DIR / "comparison_result.json"
OUTPUT_FILE = BASE_DIR / "price_data.xlsx"


def main() -> None:
    with MOBILE_FILE.open(encoding="utf-8") as f:
        mobile = json.load(f)
    with COMPARISON_FILE.open(encoding="utf-8") as f:
        comparison = json.load(f)

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        pd.DataFrame(mobile).to_excel(writer, sheet_name="mobile_data", index=False)
        pd.DataFrame(comparison).to_excel(writer, sheet_name="comparison_result", index=False)

    print(f"mobile_data: {len(mobile)} dong")
    print(f"comparison_result: {len(comparison)} dong")
    print(f"Da luu: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
