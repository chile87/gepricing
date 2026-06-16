"""
Price Tracker - Crawl dien thoai tu FPT, Hoang Ha, CellphoneS bang Firecrawl API.
Ho tro pagination (trang 1-5) hoac crawl mode (max 50 trang).
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import requests
from tqdm import tqdm

FIRECRAWL_API_KEY = "YOUR_FIRECRAWL_API_KEY"
FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v2"

MAX_PAGES = 5
CRAWL_MODE = "pagination"  # "pagination" | "crawl"
CRAWL_MAX_PAGES = 50
TARGET_MIN_PRODUCTS = 300
REQUEST_TIMEOUT = 120
RETRY_COUNT = 3
RETRY_DELAY_SEC = 5

OUTPUT_FILE = Path(__file__).parent / "mobile_data.json"

PRODUCT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "products": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dong_may": {"type": "string"},
                    "ram": {"type": "string"},
                    "rom": {"type": "string"},
                    "mau_sac": {"type": ["string", "null"]},
                    "gia_ban": {"type": "integer"},
                    "ten_cua_hang": {"type": "string"},
                },
                "required": ["dong_may", "ram", "rom", "gia_ban", "ten_cua_hang"],
            },
        }
    },
    "required": ["products"],
}

EXTRACT_PROMPT = """
Trich xuat TAT CA dien thoai hien thi tren trang danh muc (bao gom san pham sau khi load them/scroll).

Voi MOI san pham, boc tach thanh cac truong:
- dong_may: Ten dong may KHONG gom RAM/ROM/mau sac. VD: "Samsung Galaxy S26 Ultra", "iPhone 17 Pro Max".
- ram: Dung luong RAM, format "12GB", "8GB". Neu chi co ROM (iPhone) thi de "null" hoac bo qua field.
- rom: Dung luong bo nho trong, format "256GB", "512GB", "1TB".
- mau_sac: Ten mau neu co tren listing, khong co thi null.
- gia_ban: Gia ban HIEN TAI (so nguyen VND, bo dau cham/phay/ky tu dong).
- ten_cua_hang: Dung CHINH XAC ten cu hang duoc chi dinh trong prompt.

Quy tac boc tach:
- "Samsung Galaxy S26 Ultra 5G 12GB 256GB" -> dong_may="Samsung Galaxy S26 Ultra", ram="12GB", rom="256GB"
- "iPhone 17 256GB" -> dong_may="iPhone 17", ram=null hoac bo qua, rom="256GB"
- TUYET DOI khong gop nhieu cau hinh thanh 1 dong.
- Bo qua phu kien, may cu, hang sap ve.
"""

LOAD_MORE_JS = """
(() => {
  const keywords = ['Xem thêm', 'Xem thêm kết quả', 'Xem tiếp', 'Load more'];
  const nodes = [...document.querySelectorAll('button, a, span, div')];
  const target = nodes.find((el) => {
    const text = (el.textContent || '').trim();
    return keywords.some((k) => text.includes(k)) && text.length < 40;
  });
  if (target) {
    target.click();
    return 'clicked';
  }
  window.scrollTo(0, document.body.scrollHeight);
  return 'scrolled';
})();
"""


@dataclass(frozen=True)
class StoreConfig:
    ten_cua_hang: str
    base_url: str
    page_url: Callable[[int], str]
    use_load_more: bool = True
    extra_urls: tuple[str, ...] = field(default_factory=tuple)


STORES: list[StoreConfig] = [
    StoreConfig(
        ten_cua_hang="FPT",
        base_url="https://fptshop.com.vn/dien-thoai",
        page_url=lambda page: (
            "https://fptshop.com.vn/dien-thoai"
            if page == 1
            else f"https://fptshop.com.vn/dien-thoai?page={page}"
        ),
        use_load_more=True,
        extra_urls=(
            "https://fptshop.com.vn/dien-thoai/dien-thoai-5g",
            "https://fptshop.com.vn/dien-thoai/android",
        ),
    ),
    StoreConfig(
        ten_cua_hang="Hoàng Hà",
        base_url="https://hoanghamobile.com/dien-thoai-di-dong",
        page_url=lambda page: (
            "https://hoanghamobile.com/dien-thoai-di-dong"
            if page == 1
            else f"https://hoanghamobile.com/dien-thoai-di-dong?page={page}"
        ),
        use_load_more=True,
    ),
    StoreConfig(
        ten_cua_hang="Cellphones",
        base_url="https://cellphones.com.vn/mobile.html",
        page_url=lambda page: (
            "https://cellphones.com.vn/mobile.html"
            if page == 1
            else f"https://cellphones.com.vn/mobile/p{page}.html"
        ),
        use_load_more=True,
    ),
]


class FirecrawlClient:
    def __init__(self, api_key: str) -> None:
        if not api_key or api_key == "YOUR_FIRECRAWL_API_KEY":
            raise ValueError("Vui long cau hinh FIRECRAWL_API_KEY trong crawl_mobile.py")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    def scrape_products(
        self,
        url: str,
        ten_cua_hang: str,
        page_num: int,
        use_load_more: bool,
    ) -> list[dict[str, Any]]:
        prompt = (
            f"{EXTRACT_PROMPT}\n\n"
            f"ten_cua_hang cho TAT CA san pham trong response phai la: \"{ten_cua_hang}\""
        )

        actions: list[dict[str, Any]] = [
            {"type": "wait", "milliseconds": 4000},
            {"type": "scroll", "direction": "down"},
            {"type": "wait", "milliseconds": 2000},
        ]

        if use_load_more and page_num > 1:
            for _ in range(page_num - 1):
                actions.extend(
                    [
                        {"type": "executeJavascript", "script": LOAD_MORE_JS},
                        {"type": "wait", "milliseconds": 2500},
                        {"type": "scroll", "direction": "down"},
                        {"type": "wait", "milliseconds": 1500},
                    ]
                )

        payload: dict[str, Any] = {
            "url": url,
            "formats": [
                {
                    "type": "json",
                    "prompt": prompt,
                    "schema": PRODUCT_SCHEMA,
                }
            ],
            "waitFor": 6000,
            "timeout": REQUEST_TIMEOUT * 1000,
            "location": {"country": "VN", "languages": ["vi"]},
            "actions": actions,
        }

        response = self._session.post(
            f"{FIRECRAWL_BASE_URL}/scrape",
            json=payload,
            timeout=REQUEST_TIMEOUT + 30,
        )
        response.raise_for_status()
        body = response.json()

        if not body.get("success"):
            raise RuntimeError(f"Firecrawl scrape that bai: {body.get('error', body)}")

        data = body.get("data") or {}
        json_data = data.get("json") or data.get("extract") or {}
        if isinstance(json_data, list):
            return self._normalize_products(json_data, ten_cua_hang)

        products = json_data.get("products", [])
        return self._normalize_products(products, ten_cua_hang)

    def crawl_products(self, store: StoreConfig) -> list[dict[str, Any]]:
        prompt = (
            f"{EXTRACT_PROMPT}\n\n"
            f"ten_cua_hang cho TAT CA san pham phai la: \"{store.ten_cua_hang}\""
        )

        payload: dict[str, Any] = {
            "url": store.base_url,
            "limit": CRAWL_MAX_PAGES,
            "maxDiscoveryDepth": 2,
            "allowExternalLinks": False,
            "deduplicateSimilarURLs": True,
            "scrapeOptions": {
                "formats": [
                    {
                        "type": "json",
                        "prompt": prompt,
                        "schema": PRODUCT_SCHEMA,
                    }
                ],
                "waitFor": 6000,
                "location": {"country": "VN", "languages": ["vi"]},
            },
        }

        start_resp = self._session.post(
            f"{FIRECRAWL_BASE_URL}/crawl",
            json=payload,
            timeout=60,
        )
        start_resp.raise_for_status()
        start_body = start_resp.json()

        if not start_body.get("success"):
            raise RuntimeError(f"Firecrawl crawl that bai: {start_body.get('error', start_body)}")

        job_id = start_body.get("id")
        if not job_id:
            raise RuntimeError("Firecrawl crawl khong tra ve job id.")

        while True:
            status_resp = self._session.get(
                f"{FIRECRAWL_BASE_URL}/crawl/{job_id}",
                timeout=60,
            )
            status_resp.raise_for_status()
            status_body = status_resp.json()
            status = status_body.get("status")

            if status == "completed":
                return self._flatten_crawl_results(status_body, store.ten_cua_hang)

            if status == "failed":
                raise RuntimeError(f"Crawl job failed: {status_body.get('error', status_body)}")

            time.sleep(5)

    def _flatten_crawl_results(
        self,
        crawl_body: dict[str, Any],
        ten_cua_hang: str,
    ) -> list[dict[str, Any]]:
        all_products: list[dict[str, Any]] = []
        for page in crawl_body.get("data", []):
            json_data = (page.get("json") or {}) if isinstance(page, dict) else {}
            if isinstance(json_data, list):
                all_products.extend(self._normalize_products(json_data, ten_cua_hang))
                continue
            products = json_data.get("products", [])
            all_products.extend(self._normalize_products(products, ten_cua_hang))
        return all_products

    @staticmethod
    def _normalize_products(
        products: list[dict[str, Any]],
        ten_cua_hang: str,
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []

        for item in products:
            try:
                dong_may = str(item.get("dong_may", "")).strip()
                ram = item.get("ram")
                rom = str(item.get("rom", "")).strip()
                gia_ban = int(item.get("gia_ban", 0))

                if not dong_may or not rom or gia_ban <= 0:
                    continue

                normalized.append(
                    {
                        "dong_may": dong_may,
                        "ram": normalize_storage(ram) if ram else None,
                        "rom": normalize_storage(rom),
                        "mau_sac": item.get("mau_sac"),
                        "gia_ban": gia_ban,
                        "ten_cua_hang": ten_cua_hang,
                    }
                )
            except (TypeError, ValueError):
                continue

        return normalized


def normalize_storage(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", "", str(value).upper())
    if not text:
        return None
    if text.isdigit():
        return f"{text}GB"
    return text


def product_key(product: dict[str, Any]) -> tuple[str, str | None, str, str | None]:
    return (
        product["ten_cua_hang"],
        product["dong_may"].strip().lower(),
        product.get("ram"),
        product["rom"],
        str(product.get("mau_sac") or "").strip().lower() or None,
    )


def deduplicate_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str | None, str, str | None]] = set()
    unique: list[dict[str, Any]] = []

    for product in products:
        key = product_key(product)
        if key in seen:
            continue
        seen.add(key)
        unique.append(product)

    return unique


def scrape_store_pagination(
    client: FirecrawlClient,
    store: StoreConfig,
    progress_bar: tqdm,
) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []

    urls_to_scrape: list[tuple[str, int]] = [
        (store.page_url(page), page) for page in range(1, MAX_PAGES + 1)
    ]

    for extra_url in store.extra_urls:
        urls_to_scrape.append((extra_url, 1))

    for url, page_num in urls_to_scrape:
        progress_bar.set_description(f"{store.ten_cua_hang} | trang {page_num}")

        for attempt in range(1, RETRY_COUNT + 1):
            try:
                batch = client.scrape_products(
                    url=url,
                    ten_cua_hang=store.ten_cua_hang,
                    page_num=page_num,
                    use_load_more=store.use_load_more,
                )
                collected.extend(batch)
                progress_bar.set_postfix(
                    store=store.ten_cua_hang,
                    page=page_num,
                    batch=len(batch),
                    total=len(collected),
                )
                break
            except Exception as exc:
                if attempt == RETRY_COUNT:
                    print(
                        f"\n[Canh bao] {store.ten_cua_hang} trang {page_num} that bai sau {RETRY_COUNT} lan: {exc}",
                        file=sys.stderr,
                    )
                else:
                    time.sleep(RETRY_DELAY_SEC * attempt)
        progress_bar.update(1)

    return collected


def crawl_all_stores(client: FirecrawlClient) -> list[dict[str, Any]]:
    all_products: list[dict[str, Any]] = []

    for store in tqdm(STORES, desc="Crawl mode", unit="store"):
        try:
            batch = client.crawl_products(store)
            all_products.extend(batch)
            tqdm.write(f"{store.ten_cua_hang}: +{len(batch)} SP (tong tam: {len(all_products)})")
        except Exception as exc:
            print(f"[Canh bao] Crawl {store.ten_cua_hang} that bai: {exc}", file=sys.stderr)

    return all_products


def save_products(products: list[dict[str, Any]], filepath: Path) -> None:
    with filepath.open("w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


def main() -> int:
    try:
        client = FirecrawlClient(FIRECRAWL_API_KEY)
        all_products: list[dict[str, Any]] = []

        if CRAWL_MODE == "crawl":
            all_products = crawl_all_stores(client)
        else:
            total_tasks = sum(
                MAX_PAGES + len(store.extra_urls) for store in STORES
            )
            with tqdm(total=total_tasks, desc="Dang cao", unit="trang") as progress_bar:
                for store in STORES:
                    batch = scrape_store_pagination(client, store, progress_bar)
                    all_products.extend(batch)

        all_products = deduplicate_products(all_products)
        save_products(all_products, OUTPUT_FILE)

        print(f"\nHoan tat: {len(all_products)} san pham -> {OUTPUT_FILE}")
        if len(all_products) < TARGET_MIN_PRODUCTS:
            print(
                f"[Canh bao] Moi dat {len(all_products)}/{TARGET_MIN_PRODUCTS} SP. "
                "Co the tang MAX_PAGES hoac chuyen CRAWL_MODE='crawl'.",
                file=sys.stderr,
            )
        return 0

    except FileNotFoundError as exc:
        print(f"[Loi] {exc}", file=sys.stderr)
    except json.JSONDecodeError as exc:
        print(f"[Loi] JSON khong hop le: {exc}", file=sys.stderr)
    except requests.RequestException as exc:
        print(f"[Loi] Firecrawl API: {exc}", file=sys.stderr)
    except ValueError as exc:
        print(f"[Loi] {exc}", file=sys.stderr)
    except Exception as exc:
        print(f"[Loi] Crawl that bai: {exc}", file=sys.stderr)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
