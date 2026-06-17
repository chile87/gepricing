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


def load_market_payload(file_path: str | None = None) -> list[dict]:
    source_file = Path(file_path) if file_path else DEFAULT_MOBILE_JSON_PATH
    return json.loads(source_file.read_text(encoding="utf-8"))


def replace_market_data_from_payload(
    session: Session,
    payload: list[dict],
    source_name: str = "mobile_data.json",
) -> dict[str, int]:
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

    session.exec(
        text(
            """
            TRUNCATE TABLE
                applied_price_changes,
                approval_log,
                competitor_prices,
                competitor_listings,
                crawler_runs,
                inventory_snapshots,
                market_alerts,
                price_comparisons,
                price_recommendations,
                recommendation_events,
                sales_metrics_hourly,
                skus,
                strategies,
                strategy_rules,
                strategy_runs,
                ui_change_feed,
                competitor_sources,
                categories
            RESTART IDENTITY CASCADE
            """
        )
    )

    category_id = str(uuid4())
    session.exec(
        text("INSERT INTO categories (id, code, name) VALUES (:id, 'mobile', 'Mobile')"),
        params={"id": category_id},
    )

    store_names = sorted({(row.get("ten_cua_hang") or "Unknown").strip() for row in payload})
    store_sources: dict[str, dict[str, str]] = {}
    now = datetime.now(timezone.utc)

    for store_name in store_names:
        source_id = str(uuid4())
        code = re.sub(r"[^a-z0-9]+", "-", store_name.lower()).strip("-") or "unknown"
        session.exec(
            text(
                """
                INSERT INTO competitor_sources (id, code, name, base_url, is_active, created_at, updated_at)
                VALUES (:id, :code, :name, NULL, TRUE, :created_at, :updated_at)
                """
            ),
            params={
                "id": source_id,
                "code": code,
                "name": store_name,
                "created_at": now,
                "updated_at": now,
            },
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
            sku_id = str(uuid4())
            display_name = " ".join(part for part in [model_name, ram, rom] if part)
            sku_code = f"MB-{re.sub(r'[^A-Z0-9]+', '-', display_name.upper()).strip('-')[:48] or index}"
            cost_price = int((Decimal(sale_price) * Decimal("0.70")).quantize(Decimal("1")))
            inventory = int((sale_price % 97) + 20)

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
                    """
                ),
                params={
                    "id": sku_id,
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

        listing_id = str(uuid4())
        sku_id = str(sku_map[sku_key]["id"])
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
                """
            ),
            params={
                "id": listing_id,
                "sku_id": sku_id,
                "competitor_source_id": source["id"],
                "competitor_sku": f"{source['code']}-{index}",
                "competitor_product_name": str(sku_map[sku_key]["name"]),
                "product_url": f"https://{source['code']}.local/product/{index}",
                "created_at": now,
                "updated_at": now,
            },
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
                "url": f"https://{source['code']}.local/product/{index}",
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
