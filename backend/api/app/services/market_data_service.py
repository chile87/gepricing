from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
from uuid import uuid4

from sqlalchemy import text
from sqlmodel import Session


DEFAULT_MOBILE_JSON_PATH = Path(__file__).resolve().parents[3] / "crawlPrice" / "mobile_data.json"
DEFAULT_COMPARISON_JSON_PATH = Path(__file__).resolve().parents[3] / "crawlPrice" / "comparison_result.json"


def load_market_payload(file_path: str | None = None) -> list[dict]:
    source_file = Path(file_path) if file_path else DEFAULT_MOBILE_JSON_PATH
    return json.loads(source_file.read_text(encoding="utf-8"))


def load_comparison_payload(file_path: str | None = None) -> list[dict]:
    source_file = Path(file_path) if file_path else DEFAULT_COMPARISON_JSON_PATH
    return json.loads(source_file.read_text(encoding="utf-8"))


def _ensure_price_comparisons_table(session: Session) -> None:
    session.exec(
        text(
            """
            CREATE TABLE IF NOT EXISTS price_comparisons (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                sku_id UUID NOT NULL REFERENCES skus(id) ON DELETE CASCADE UNIQUE,
                competitor_count INTEGER NOT NULL DEFAULT 0,
                lowest_competitor_price NUMERIC(14, 2),
                average_competitor_price NUMERIC(14, 2),
                highest_competitor_price NUMERIC(14, 2),
                price_gap_value NUMERIC(14, 2),
                price_gap_pct NUMERIC(8, 2),
                lowest_competitor_source VARCHAR(64),
                snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT chk_price_comparisons_competitor_count CHECK (competitor_count >= 0)
            )
            """
        )
    )


def replace_market_data_from_payload(
    session: Session,
    payload: list[dict],
    source_name: str = "mobile_data.json",
) -> dict[str, int]:
    _ensure_price_comparisons_table(session)

    category_id = str(
        session.exec(
            text(
                """
                INSERT INTO categories (id, code, name)
                VALUES (:id, 'mobile', 'Mobile')
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name
                RETURNING id
                """
            ),
            params={"id": str(uuid4())},
        ).one()[0]
    )

    store_names = sorted({(row.get("ten_cua_hang") or "Unknown").strip() for row in payload})
    store_sources: dict[str, dict[str, str]] = {}
    now = datetime.now(timezone.utc)

    for store_name in store_names:
        code = re.sub(r"[^a-z0-9]+", "-", store_name.lower()).strip("-") or "unknown"
        source_id = str(
            session.exec(
                text(
                    """
                    INSERT INTO competitor_sources (id, code, name, base_url, is_active, created_at, updated_at)
                    VALUES (:id, :code, :name, NULL, TRUE, :created_at, :updated_at)
                    ON CONFLICT (code) DO UPDATE SET
                        name = EXCLUDED.name,
                        is_active = TRUE,
                        updated_at = EXCLUDED.updated_at
                    RETURNING id
                    """
                ),
                params={
                    "id": str(uuid4()),
                    "code": code,
                    "name": store_name,
                    "created_at": now,
                    "updated_at": now,
                },
            ).one()[0]
        )
        crawler_run_id = str(uuid4())
        session.exec(
            text(
                """
                INSERT INTO crawler_runs (
                    id, source_id, status, started_at, finished_at, pages_crawled, items_found, metadata
                ) VALUES (
                    :id, :source_id, 'completed', :started_at, :finished_at, 1, 0, CAST(:metadata AS jsonb)
                )
                """
            ),
            params={
                "id": crawler_run_id,
                "source_id": source_id,
                "started_at": now,
                "finished_at": now,
                "metadata": json.dumps({"source": source_name, "store": store_name}),
            },
        )
        store_sources[store_name] = {"id": source_id, "code": code, "crawler_run_id": crawler_run_id}

    sku_map: dict[tuple[str, str | None, str | None], dict[str, str | int]] = {}

    for index, row in enumerate(payload, start=1):
        model_name = (row.get("dong_may") or "Unknown Model").strip()
        ram = (row.get("ram") or "").strip() or None
        rom = (row.get("rom") or "").strip() or None
        sale_price = int(row.get("gia_ban") or 0) or 1_000_000
        store_name = (row.get("ten_cua_hang") or "Unknown").strip()
        source = store_sources[store_name]
        sku_key = (model_name.lower(), (ram or "").lower() or None, (rom or "").lower() or None)

        if sku_key not in sku_map:
            display_name = " ".join(part for part in [model_name, ram, rom] if part)
            sku_code = f"MB-{re.sub(r'[^A-Z0-9]+', '-', display_name.upper()).strip('-')[:48] or index}"
            cost_price = int((Decimal(sale_price) * Decimal("0.70")).quantize(Decimal("1")))
            inventory = int((sale_price % 97) + 20)

            sku_id = str(
                session.exec(
                    text(
                        """
                        INSERT INTO skus (
                            id, sku_code, name, category_id, category, brand, cost_price, current_price,
                            currency, inventory, reorder_point, is_active, created_at, updated_at
                        ) VALUES (
                            :id, :sku_code, :name, :category_id, 'Mobile', :brand, :cost_price, :current_price,
                            'VND', :inventory, :reorder_point, TRUE, :created_at, :updated_at
                        )
                        ON CONFLICT (sku_code) DO UPDATE SET
                            name = EXCLUDED.name,
                            category_id = EXCLUDED.category_id,
                            category = EXCLUDED.category,
                            brand = EXCLUDED.brand,
                            cost_price = EXCLUDED.cost_price,
                            current_price = EXCLUDED.current_price,
                            inventory = EXCLUDED.inventory,
                            reorder_point = EXCLUDED.reorder_point,
                            is_active = TRUE,
                            updated_at = EXCLUDED.updated_at
                        RETURNING id
                        """
                    ),
                    params={
                        "id": str(uuid4()),
                        "sku_code": sku_code,
                        "name": display_name,
                        "category_id": category_id,
                        "brand": (model_name.split(" ", 1)[0] if model_name else "Unknown")[:128],
                        "cost_price": cost_price,
                        "current_price": sale_price,
                        "inventory": inventory,
                        "reorder_point": max(5, inventory // 4),
                        "created_at": now,
                        "updated_at": now,
                    },
                ).one()[0]
            )

            session.exec(
                text(
                    """
                    INSERT INTO inventory_snapshots (
                        id, sku_id, on_hand_qty, reserved_qty, inbound_qty, snapshot_at, created_at
                    ) VALUES (
                        :id, :sku_id, :on_hand_qty, :reserved_qty, :inbound_qty, :snapshot_at, :created_at
                    )
                    """
                ),
                params={
                    "id": str(uuid4()),
                    "sku_id": sku_id,
                    "on_hand_qty": inventory,
                    "reserved_qty": max(1, inventory // 10),
                    "inbound_qty": max(0, inventory // 8),
                    "snapshot_at": now,
                    "created_at": now,
                },
            )

            units_sold = max(1, inventory // 6)
            session.exec(
                text(
                    """
                    INSERT INTO sales_metrics_hourly (
                        id, sku_id, period_start, units_sold, revenue, margin_value, promo_spend,
                        conversion_rate, created_at
                    ) VALUES (
                        :id, :sku_id, :period_start, :units_sold, :revenue, :margin_value, 0, :conversion_rate, :created_at
                    )
                    """
                ),
                params={
                    "id": str(uuid4()),
                    "sku_id": sku_id,
                    "period_start": now.replace(minute=0, second=0, microsecond=0),
                    "units_sold": units_sold,
                    "revenue": sale_price * units_sold,
                    "margin_value": (sale_price - cost_price) * units_sold,
                    "conversion_rate": Decimal("0.12"),
                    "created_at": now,
                },
            )

            sku_map[sku_key] = {"id": sku_id, "name": display_name, "inventory": inventory}

        sku_id = str(sku_map[sku_key]["id"])
        product_url = f"https://{source['code']}.local/product/{index}"
        listing_id = str(
            session.exec(
                text(
                    """
                    INSERT INTO competitor_listings (
                        id, sku_id, competitor_source_id, competitor_sku, competitor_product_name,
                        product_url, is_active, created_at, updated_at
                    ) VALUES (
                        :id, :sku_id, :competitor_source_id, :competitor_sku, :competitor_product_name,
                        :product_url, TRUE, :created_at, :updated_at
                    )
                    ON CONFLICT (sku_id, competitor_source_id, product_url) DO UPDATE SET
                        competitor_sku = EXCLUDED.competitor_sku,
                        competitor_product_name = EXCLUDED.competitor_product_name,
                        is_active = TRUE,
                        updated_at = EXCLUDED.updated_at
                    RETURNING id
                    """
                ),
                params={
                    "id": str(uuid4()),
                    "sku_id": sku_id,
                    "competitor_source_id": source["id"],
                    "competitor_sku": f"{source['code']}-{index}",
                    "competitor_product_name": str(sku_map[sku_key]["name"]),
                    "product_url": product_url,
                    "created_at": now,
                    "updated_at": now,
                },
            ).one()[0]
        )
        session.exec(
            text(
                """
                INSERT INTO competitor_prices (
                    id, sku_id, competitor_source_id, competitor_listing_id, crawler_run_id,
                    source, price, original_price, promo_price, currency, availability, stock_status,
                    url, crawled_at, created_at
                ) VALUES (
                    :id, :sku_id, :competitor_source_id, :competitor_listing_id, :crawler_run_id,
                    :source, :price, :original_price, NULL, 'VND', 'in_stock', 'available',
                    :url, :crawled_at, :created_at
                )
                """
            ),
            params={
                "id": str(uuid4()),
                "sku_id": sku_id,
                "competitor_source_id": source["id"],
                "competitor_listing_id": listing_id,
                "crawler_run_id": source["crawler_run_id"],
                "source": source["code"],
                "price": sale_price,
                "original_price": sale_price,
                "url": product_url,
                "crawled_at": now,
                "created_at": now,
            },
        )

    session.exec(
        text(
            """
            UPDATE crawler_runs cr
            SET items_found = counts.item_count
            FROM (
                SELECT competitor_source_id AS source_id, COUNT(*) AS item_count
                FROM competitor_prices
                GROUP BY competitor_source_id
            ) counts
            WHERE cr.source_id = counts.source_id
            """
        )
    )

    return {
        "categories": 1,
        "competitorSources": len(store_sources),
        "skus": len(sku_map),
        "competitorListings": len(payload),
        "competitorPrices": len(payload),
        "inventorySnapshots": len(sku_map),
        "salesMetricsHourly": len(sku_map),
    }


def replace_market_data_from_file(session: Session, file_path: str | None = None) -> dict[str, int]:
    payload = load_market_payload(file_path)
    return replace_market_data_from_payload(session, payload, Path(file_path).name if file_path else DEFAULT_MOBILE_JSON_PATH.name)


def replace_market_data_from_comparison_payload(
    session: Session,
    payload: list[dict],
    source_name: str = "comparison_result.json",
) -> dict[str, int]:
    _ensure_price_comparisons_table(session)

    now = datetime.now(timezone.utc)
    categories: dict[str, str] = {}
    competitor_sources: dict[str, dict[str, str]] = {}
    sku_map: dict[tuple[str, str], dict[str, str | int]] = {}
    category_codes: set[str] = set()
    source_codes: set[str] = set()
    sku_codes: set[str] = set()

    def make_unique_code(base: str, used_codes: set[str], max_length: int) -> str:
        candidate = (base or "unknown")[:max_length]
        suffix = 2
        while candidate in used_codes:
            suffix_token = f"-{suffix}"
            candidate = f"{(base or 'unknown')[: max_length - len(suffix_token)]}{suffix_token}"
            suffix += 1
        used_codes.add(candidate)
        return candidate

    for row in payload:
        category_name = (row.get("Ngành hàng") or "Uncategorized").strip() or "Uncategorized"
        if category_name not in categories:
            category_code_base = re.sub(r"[^a-z0-9]+", "-", category_name.lower()).strip("-") or "uncategorized"
            category_code = make_unique_code(category_code_base, category_codes, 64)
            category_id = str(
                session.exec(
                    text(
                        """
                        INSERT INTO categories (id, code, name)
                        VALUES (:id, :code, :name)
                        ON CONFLICT (code) DO UPDATE SET
                            name = EXCLUDED.name
                        RETURNING id
                        """
                    ),
                    params={"id": str(uuid4()), "code": category_code, "name": category_name[:128]},
                ).one()[0]
            )
            categories[category_name] = category_id

    qualified_rows = [
        row
        for row in payload
        if float(row.get("LLM Confident (%)") or 0) == 100.0
    ]

    source_names = sorted({(row.get("Tên Đối thủ") or "Unknown").strip() or "Unknown" for row in qualified_rows})
    for source_name_raw in source_names:
        code_base = re.sub(r"[^a-z0-9]+", "-", source_name_raw.lower()).strip("-") or "unknown"
        code = make_unique_code(code_base, source_codes, 64)
        source_id = str(
            session.exec(
                text(
                    """
                    INSERT INTO competitor_sources (id, code, name, base_url, is_active, created_at, updated_at)
                    VALUES (:id, :code, :name, NULL, TRUE, :created_at, :updated_at)
                    ON CONFLICT (code) DO UPDATE SET
                        name = EXCLUDED.name,
                        is_active = TRUE,
                        updated_at = EXCLUDED.updated_at
                    RETURNING id
                    """
                ),
                params={
                    "id": str(uuid4()),
                    "code": code,
                    "name": source_name_raw[:128],
                    "created_at": now,
                    "updated_at": now,
                },
            ).one()[0]
        )
        crawler_run_id = str(uuid4())
        session.exec(
            text(
                """
                INSERT INTO crawler_runs (
                    id, source_id, status, started_at, finished_at, pages_crawled, items_found, metadata
                ) VALUES (
                    :id, :source_id, 'completed', :started_at, :finished_at, 1, 0, CAST(:metadata AS jsonb)
                )
                """
            ),
            params={
                "id": crawler_run_id,
                "source_id": source_id,
                "started_at": now,
                "finished_at": now,
                "metadata": json.dumps({"source": source_name, "store": source_name_raw}),
            },
        )
        competitor_sources[source_name_raw] = {"id": source_id, "code": code, "crawler_run_id": crawler_run_id}

    listings_inserted = 0
    prices_inserted = 0

    for index, row in enumerate(payload, start=1):
        fpt_name = str(row.get("Tên SKU FPT Shop") or "Unknown SKU").strip() or "Unknown SKU"
        category_name = (row.get("Ngành hàng") or "Uncategorized").strip() or "Uncategorized"
        category_id = categories[category_name]
        fpt_price = int(row.get("Giá FPT Shop") or 0)
        competitor_price = int(row.get("Giá Đối thủ") or 0)
        source_name_raw = (row.get("Tên Đối thủ") or "Unknown").strip() or "Unknown"

        sku_key = (category_name.lower(), fpt_name.lower())
        if sku_key not in sku_map:
            sku_code_base = re.sub(r"[^A-Z0-9]+", "-", fpt_name.upper()).strip("-")
            category_code_token = re.sub(r"[^A-Z0-9]+", "-", category_name.upper()).strip("-") or "CAT"
            sku_code = make_unique_code(
                f"CMP-{category_code_token[:12]}-{sku_code_base[:36] or index}",
                sku_codes,
                64,
            )
            current_price = max(fpt_price, 0)
            cost_price = int((Decimal(max(current_price, 1)) * Decimal("0.70")).quantize(Decimal("1")))
            inventory = int((max(current_price, 1) % 97) + 20)

            raw_brand = (str(row.get("dong_may_goc") or fpt_name).strip().split(" ", 1)[0] or "Unknown")[:128]
            sku_id = str(
                session.exec(
                    text(
                        """
                        INSERT INTO skus (
                            id, sku_code, name, category_id, category, brand, cost_price, current_price,
                            currency, inventory, reorder_point, is_active, created_at, updated_at
                        ) VALUES (
                            :id, :sku_code, :name, :category_id, :category, :brand, :cost_price, :current_price,
                            'VND', :inventory, :reorder_point, TRUE, :created_at, :updated_at
                        )
                        ON CONFLICT (sku_code) DO UPDATE SET
                            name = EXCLUDED.name,
                            category_id = EXCLUDED.category_id,
                            category = EXCLUDED.category,
                            brand = EXCLUDED.brand,
                            cost_price = EXCLUDED.cost_price,
                            current_price = EXCLUDED.current_price,
                            inventory = EXCLUDED.inventory,
                            reorder_point = EXCLUDED.reorder_point,
                            is_active = TRUE,
                            updated_at = EXCLUDED.updated_at
                        RETURNING id
                        """
                    ),
                    params={
                        "id": str(uuid4()),
                        "sku_code": sku_code,
                        "name": fpt_name,
                        "category_id": category_id,
                        "category": category_name[:128],
                        "brand": raw_brand,
                        "cost_price": cost_price,
                        "current_price": current_price,
                        "inventory": inventory,
                        "reorder_point": max(5, inventory // 4),
                        "created_at": now,
                        "updated_at": now,
                    },
                ).one()[0]
            )

            session.exec(
                text(
                    """
                    INSERT INTO inventory_snapshots (
                        id, sku_id, on_hand_qty, reserved_qty, inbound_qty, snapshot_at, created_at
                    ) VALUES (
                        :id, :sku_id, :on_hand_qty, :reserved_qty, :inbound_qty, :snapshot_at, :created_at
                    )
                    """
                ),
                params={
                    "id": str(uuid4()),
                    "sku_id": sku_id,
                    "on_hand_qty": inventory,
                    "reserved_qty": max(1, inventory // 10),
                    "inbound_qty": max(0, inventory // 8),
                    "snapshot_at": now,
                    "created_at": now,
                },
            )

            units_sold = max(1, inventory // 6)
            session.exec(
                text(
                    """
                    INSERT INTO sales_metrics_hourly (
                        id, sku_id, period_start, units_sold, revenue, margin_value, promo_spend,
                        conversion_rate, created_at
                    ) VALUES (
                        :id, :sku_id, :period_start, :units_sold, :revenue, :margin_value, 0, :conversion_rate, :created_at
                    )
                    """
                ),
                params={
                    "id": str(uuid4()),
                    "sku_id": sku_id,
                    "period_start": now.replace(minute=0, second=0, microsecond=0),
                    "units_sold": units_sold,
                    "revenue": current_price * units_sold,
                    "margin_value": (current_price - cost_price) * units_sold,
                    "conversion_rate": Decimal("0.12"),
                    "created_at": now,
                },
            )

            sku_map[sku_key] = {"id": sku_id}

        if float(row.get("LLM Confident (%)") or 0) == 100.0:
            source = competitor_sources[source_name_raw]
            sku_id = str(sku_map[sku_key]["id"])
            competitor_sku = str(row.get("SKU Đối thủ") or "").strip() or None
            competitor_product_name = competitor_sku or str(row.get("dong_may_goc") or fpt_name).strip()
            product_url = f"https://{source['code']}.local/product/{index}"

            listing_id = str(
                session.exec(
                    text(
                        """
                        INSERT INTO competitor_listings (
                            id, sku_id, competitor_source_id, competitor_sku, competitor_product_name,
                            product_url, is_active, created_at, updated_at
                        ) VALUES (
                            :id, :sku_id, :competitor_source_id, :competitor_sku, :competitor_product_name,
                            :product_url, TRUE, :created_at, :updated_at
                        )
                        ON CONFLICT (sku_id, competitor_source_id, product_url) DO UPDATE SET
                            competitor_sku = EXCLUDED.competitor_sku,
                            competitor_product_name = EXCLUDED.competitor_product_name,
                            is_active = TRUE,
                            updated_at = EXCLUDED.updated_at
                        RETURNING id
                        """
                    ),
                    params={
                        "id": str(uuid4()),
                        "sku_id": sku_id,
                        "competitor_source_id": source["id"],
                        "competitor_sku": competitor_sku[:128] if competitor_sku else None,
                        "competitor_product_name": competitor_product_name,
                        "product_url": product_url,
                        "created_at": now,
                        "updated_at": now,
                    },
                ).one()[0]
            )
            listings_inserted += 1

            if competitor_price > 0:
                session.exec(
                    text(
                        """
                        INSERT INTO competitor_prices (
                            id, sku_id, competitor_source_id, competitor_listing_id, crawler_run_id,
                            source, price, original_price, promo_price, currency, availability, stock_status,
                            url, crawled_at, created_at
                        ) VALUES (
                            :id, :sku_id, :competitor_source_id, :competitor_listing_id, :crawler_run_id,
                            :source, :price, :original_price, NULL, 'VND', 'in_stock', 'available',
                            :url, :crawled_at, :created_at
                        )
                        """
                    ),
                    params={
                        "id": str(uuid4()),
                        "sku_id": sku_id,
                        "competitor_source_id": source["id"],
                        "competitor_listing_id": listing_id,
                        "crawler_run_id": source["crawler_run_id"],
                        "source": source["code"],
                        "price": competitor_price,
                        "original_price": competitor_price,
                        "url": product_url,
                        "crawled_at": now,
                        "created_at": now,
                    },
                )
                prices_inserted += 1

    session.exec(
        text(
            """
            UPDATE crawler_runs cr
            SET items_found = counts.item_count
            FROM (
                SELECT competitor_source_id AS source_id, COUNT(*) AS item_count
                FROM competitor_prices
                GROUP BY competitor_source_id
            ) counts
            WHERE cr.source_id = counts.source_id
            """
        )
    )

    return {
        "categories": len(categories),
        "competitorSources": len(competitor_sources),
        "skus": len(sku_map),
        "competitorListings": listings_inserted,
        "competitorPrices": prices_inserted,
        "inventorySnapshots": len(sku_map),
        "salesMetricsHourly": len(sku_map),
    }


def replace_market_data_from_comparison_file(session: Session, file_path: str | None = None) -> dict[str, int]:
    payload = load_comparison_payload(file_path)
    return replace_market_data_from_comparison_payload(
        session,
        payload,
        Path(file_path).name if file_path else DEFAULT_COMPARISON_JSON_PATH.name,
    )
