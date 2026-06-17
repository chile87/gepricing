from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import text
from sqlmodel import Session

from app.services.pricing_service import apply_approval_decision
from shared.models.dashboard import (
    ApprovalPriceHistoryItem,
    AiSummary,
    AiSummaryBulletPoint,
    CompetitorSourcePriceItem,
    CopilotRecommendation,
    ImpactForecastPoint,
    ImpactForecastResponse,
    KpiMetrics,
    PricingOpportunity,
    RecommendationInboxItem,
    RecommendationInboxResponse,
    RecommendationSkuDetail,
    RecommendationSortBy,
    RecommendationSortOrder,
)


TYPE_TO_ACTION = {
    "raise": "Raise Price",
    "lower": "Lower Price",
    "promo": "Promotional Action",
    "stop": "Stop Promotion",
}

TYPE_TO_COLOR = {
    "raise": "#4d7fff",
    "lower": "#22c8a0",
    "promo": "#f5a623",
    "stop": "#e879c7",
}

EXECUTIVE_TYPES = ("raise", "lower")


def ensure_dashboard_seed_data(session: Session) -> None:
    recommendation_count = session.exec(text("SELECT COUNT(*) FROM price_recommendations")).one()[0]
    if recommendation_count:
        return

    category_rows = session.exec(text("SELECT code, id FROM categories")).mappings().all()
    category_ids = {row["code"]: row["id"] for row in category_rows}

    strategy_rows = [
        {
            "id": uuid4(),
            "name": "Competitor Guardrail",
            "description": "Match market drops while preserving margin floor.",
            "status": "active",
            "created_by": "system",
            "is_active": True,
        },
        {
            "id": uuid4(),
            "name": "Inventory Pressure",
            "description": "Lower price on overstocks with low sell-through.",
            "status": "active",
            "created_by": "system",
            "is_active": True,
        },
        {
            "id": uuid4(),
            "name": "Promo Cleanup",
            "description": "Stop promotions with weak ROI.",
            "status": "paused",
            "created_by": "system",
            "is_active": True,
        },
    ]

    for strategy in strategy_rows:
        session.exec(
            text(
                """
                INSERT INTO strategies (id, name, description, status, created_by, is_active)
                VALUES (:id, :name, :description, :status, :created_by, :is_active)
                ON CONFLICT DO NOTHING
                """
            ),
            params=strategy,
        )

    sku_rows = [
        {
            "id": uuid4(),
            "sku_code": "OLED-TV-55",
            "name": 'TV 55" OLED',
            "category_id": category_ids.get("electronics"),
            "category": "Electronics",
            "brand": "VisionX",
            "cost_price": Decimal("820.00"),
            "current_price": Decimal("1199.00"),
            "currency": "USD",
            "inventory": 44,
            "reorder_point": 8,
        },
        {
            "id": uuid4(),
            "sku_code": "LAP-PRO-14",
            "name": 'Laptop Pro 14"',
            "category_id": category_ids.get("electronics"),
            "category": "Electronics",
            "brand": "ZenByte",
            "cost_price": Decimal("980.00"),
            "current_price": Decimal("1499.00"),
            "currency": "USD",
            "inventory": 61,
            "reorder_point": 12,
        },
        {
            "id": uuid4(),
            "sku_code": "SPK-BT-01",
            "name": "Bluetooth Speaker",
            "category_id": category_ids.get("audio"),
            "category": "Audio",
            "brand": "Pulse",
            "cost_price": Decimal("54.00"),
            "current_price": Decimal("89.00"),
            "currency": "USD",
            "inventory": 85,
            "reorder_point": 15,
        },
        {
            "id": uuid4(),
            "sku_code": "WM-XL-09",
            "name": "Washing Machine",
            "category_id": category_ids.get("appliances"),
            "category": "Appliances",
            "brand": "HomeCore",
            "cost_price": Decimal("420.00"),
            "current_price": Decimal("649.00"),
            "currency": "USD",
            "inventory": 35,
            "reorder_point": 6,
        },
        {
            "id": uuid4(),
            "sku_code": "AC-18K",
            "name": "Air Conditioner",
            "category_id": category_ids.get("appliances"),
            "category": "Appliances",
            "brand": "CoolAir",
            "cost_price": Decimal("510.00"),
            "current_price": Decimal("799.00"),
            "currency": "USD",
            "inventory": 27,
            "reorder_point": 5,
        },
        {
            "id": uuid4(),
            "sku_code": "EAR-WL-02",
            "name": "Wireless Earbuds",
            "category_id": category_ids.get("audio"),
            "category": "Audio",
            "brand": "Pulse",
            "cost_price": Decimal("38.00"),
            "current_price": Decimal("79.00"),
            "currency": "USD",
            "inventory": 110,
            "reorder_point": 20,
        },
        {
            "id": uuid4(),
            "sku_code": "MON-GM-27",
            "name": "Gaming Monitor",
            "category_id": category_ids.get("electronics"),
            "category": "Electronics",
            "brand": "PixelForge",
            "cost_price": Decimal("210.00"),
            "current_price": Decimal("329.00"),
            "currency": "USD",
            "inventory": 58,
            "reorder_point": 10,
        },
        {
            "id": uuid4(),
            "sku_code": "RF-XL-02",
            "name": "Refrigerator XL",
            "category_id": category_ids.get("appliances"),
            "category": "Appliances",
            "brand": "FreshBox",
            "cost_price": Decimal("690.00"),
            "current_price": Decimal("1049.00"),
            "currency": "USD",
            "inventory": 22,
            "reorder_point": 4,
        },
        {
            "id": uuid4(),
            "sku_code": "SW-03",
            "name": "Smart Watch",
            "category_id": category_ids.get("wearables"),
            "category": "Wearables",
            "brand": "FitNova",
            "cost_price": Decimal("120.00"),
            "current_price": Decimal("199.00"),
            "currency": "USD",
            "inventory": 93,
            "reorder_point": 14,
        },
        {
            "id": uuid4(),
            "sku_code": "KB-MECH-01",
            "name": "Mechanical Keyboard",
            "category_id": category_ids.get("accessories"),
            "category": "Accessories",
            "brand": "KeyWave",
            "cost_price": Decimal("47.00"),
            "current_price": Decimal("99.00"),
            "currency": "USD",
            "inventory": 74,
            "reorder_point": 16,
        },
        {
            "id": uuid4(),
            "sku_code": "RV-200",
            "name": "Robot Vacuum",
            "category_id": category_ids.get("appliances"),
            "category": "Home",
            "brand": "CleanBot",
            "cost_price": Decimal("180.00"),
            "current_price": Decimal("319.00"),
            "currency": "USD",
            "inventory": 41,
            "reorder_point": 8,
        },
        {
            "id": uuid4(),
            "sku_code": "SB-PRO-01",
            "name": "Soundbar Pro",
            "category_id": category_ids.get("audio"),
            "category": "Audio",
            "brand": "Pulse",
            "cost_price": Decimal("145.00"),
            "current_price": Decimal("249.00"),
            "currency": "USD",
            "inventory": 36,
            "reorder_point": 8,
        },
    ]

    for sku in sku_rows:
        session.exec(
            text(
                """
                INSERT INTO skus (
                    id, sku_code, name, category_id, category, brand,
                    cost_price, current_price, currency, inventory, reorder_point, is_active
                )
                VALUES (
                    :id, :sku_code, :name, :category_id, :category, :brand,
                    :cost_price, :current_price, :currency, :inventory, :reorder_point, TRUE
                )
                ON CONFLICT (sku_code) DO NOTHING
                """
            ),
            params=sku,
        )

    recommendations = [
        ("raise", 0, Decimal("1259.00"), Decimal("31.50"), Decimal("42000.00"), Decimal("12000.00"), Decimal("4.00"), Decimal("0.91"), "High"),
        ("lower", 1, Decimal("1379.00"), Decimal("22.00"), Decimal("18000.00"), Decimal("6500.00"), Decimal("15.00"), Decimal("0.88"), "High"),
        ("raise", 2, Decimal("94.00"), Decimal("28.00"), Decimal("12000.00"), Decimal("4100.00"), Decimal("3.00"), Decimal("0.72"), "Medium"),
        ("lower", 3, Decimal("585.00"), Decimal("18.00"), Decimal("15000.00"), Decimal("5200.00"), Decimal("20.00"), Decimal("0.83"), "High"),
        ("stop", 4, Decimal("799.00"), Decimal("26.00"), Decimal("9000.00"), Decimal("18000.00"), Decimal("0.00"), Decimal("0.79"), "High"),
        ("promo", 5, Decimal("74.00"), Decimal("21.00"), Decimal("9000.00"), Decimal("3400.00"), Decimal("7.00"), Decimal("0.69"), "Medium"),
        ("raise", 6, Decimal("342.00"), Decimal("29.00"), Decimal("21000.00"), Decimal("6300.00"), Decimal("5.00"), Decimal("0.87"), "High"),
        ("lower", 7, Decimal("979.00"), Decimal("16.00"), Decimal("13000.00"), Decimal("4100.00"), Decimal("12.00"), Decimal("0.67"), "Medium"),
        ("promo", 8, Decimal("189.00"), Decimal("24.00"), Decimal("15000.00"), Decimal("5100.00"), Decimal("8.00"), Decimal("0.82"), "High"),
        ("raise", 9, Decimal("102.00"), Decimal("35.00"), Decimal("7000.00"), Decimal("2100.00"), Decimal("2.00"), Decimal("0.64"), "Medium"),
        ("lower", 10, Decimal("299.00"), Decimal("19.00"), Decimal("11000.00"), Decimal("3600.00"), Decimal("10.00"), Decimal("0.85"), "High"),
        ("stop", 11, Decimal("249.00"), Decimal("25.00"), Decimal("6000.00"), Decimal("6000.00"), Decimal("0.00"), Decimal("0.63"), "Medium"),
    ]

    now = datetime.now(timezone.utc)
    for index, row in enumerate(recommendations):
        recommendation_type, sku_index, recommended_price, margin_pct, revenue_impact, margin_impact, inventory_impact, confidence_score, confidence_label = row
        sku = sku_rows[sku_index]
        strategy = strategy_rows[index % len(strategy_rows)]
        session.exec(
            text(
                """
                INSERT INTO price_recommendations (
                    id, strategy_id, sku_id, recommendation_type, current_price, recommended_price,
                    margin_pct, expected_revenue_impact, expected_margin_impact, expected_inventory_impact,
                    confidence_score, confidence_label, rule_details, rationale, status, created_at, updated_at
                )
                VALUES (
                    :id, :strategy_id, :sku_id, :recommendation_type, :current_price, :recommended_price,
                    :margin_pct, :expected_revenue_impact, :expected_margin_impact, :expected_inventory_impact,
                    :confidence_score, :confidence_label, CAST(:rule_details AS jsonb), CAST(:rationale AS jsonb),
                    'pending', :created_at, :updated_at
                )
                """
            ),
            params={
                "id": uuid4(),
                "strategy_id": strategy["id"],
                "sku_id": sku["id"],
                "recommendation_type": recommendation_type,
                "current_price": sku["current_price"],
                "recommended_price": recommended_price,
                "margin_pct": margin_pct,
                "expected_revenue_impact": revenue_impact,
                "expected_margin_impact": margin_impact,
                "expected_inventory_impact": inventory_impact,
                "confidence_score": confidence_score,
                "confidence_label": confidence_label,
                "rule_details": '{"source":"seed","engine":"rule-based"}',
                "rationale": '{"note":"Seeded demo recommendation for UI integration"}',
                "created_at": now,
                "updated_at": now,
            },
        )

    session.commit()


def get_dashboard_kpis(session: Session, start_date: str | None, end_date: str | None) -> KpiMetrics:
    rows = _fetch_recommendation_rows(session, start_date, end_date)
    active_strategy_count = session.exec(
        text("SELECT COUNT(*) FROM strategies WHERE status = 'active' AND is_active = TRUE")
    ).one()[0]

    revenue_raise = sum(_decimal_or_zero(row["expected_revenue_impact"]) for row in rows if row["recommendation_type"] == "raise")
    margin_avg = _average([_decimal_or_zero(row["margin_pct"]) for row in rows])
    stop_margin = sum(_decimal_or_zero(row["expected_margin_impact"]) for row in rows if row["recommendation_type"] == "stop")
    overstock_count = sum(1 for row in rows if row["recommendation_type"] == "lower")

    return KpiMetrics(
        revenueOpportunity={
            "title": "Revenue Opportunity",
            "displayValue": _format_signed_currency(revenue_raise),
            "numericValue": float(revenue_raise),
            "change": {"percentage": 8.7, "isPositive": True, "periodLabel": "vs last week"},
        },
        marginOpportunity={
            "title": "Margin Opportunity",
            "displayValue": f"+{margin_avg:.1f}%",
            "numericValue": float(margin_avg),
            "change": {"percentage": 2.1, "isPositive": True, "periodLabel": "vs last week"},
        },
        promoWasteSaving={
            "title": "Promo Waste Saving",
            "displayValue": _format_signed_currency(stop_margin),
            "numericValue": float(stop_margin),
            "change": {"percentage": 12.3, "isPositive": True, "periodLabel": "vs last week"},
        },
        overstockRisk={
            "title": "Overstock Risk",
            "displayValue": str(overstock_count),
            "numericValue": overstock_count,
            "unit": "SKUs",
            "change": {"percentage": 18.0, "isPositive": False, "periodLabel": "vs last week"},
        },
        activeStrategies={
            "title": "Active Strategies",
            "displayValue": str(active_strategy_count),
            "numericValue": active_strategy_count,
            "change": {"value": 1, "isPositive": True, "periodLabel": "vs last week"},
        },
    )


def get_pricing_opportunities(session: Session) -> list[PricingOpportunity]:
    rows = _fetch_recommendation_rows(session, None, None)
    executive_rows = [row for row in rows if row["recommendation_type"] in EXECUTIVE_TYPES]
    counter = Counter(row["recommendation_type"] for row in executive_rows)
    total = max(len(executive_rows), 1)

    return [
        PricingOpportunity(
            action=TYPE_TO_ACTION[recommendation_type],
            skuCount=count,
            percentage=round((count / total) * 100),
        )
        for recommendation_type, count in (("raise", counter.get("raise", 0)), ("lower", counter.get("lower", 0)))
    ]


def get_impact_forecast(session: Session, start_date: str | None, end_date: str | None) -> ImpactForecastResponse:
    period = _resolve_period_window(start_date, end_date)
    rows = _fetch_recommendation_rows(session, period["start"], period["end"])
    previous_rows = _fetch_recommendation_rows(session, period["previousStart"], period["previousEnd"])

    revenue_current = float(sum(_decimal_or_zero(row["expected_revenue_impact"]) for row in rows))
    revenue_previous = float(sum(_decimal_or_zero(row["expected_revenue_impact"]) for row in previous_rows))
    margin_current = float(_average([_decimal_or_zero(row["margin_pct"]) for row in rows]))
    margin_previous = float(_average([_decimal_or_zero(row["margin_pct"]) for row in previous_rows]))
    inventory_current = float(sum(abs(_decimal_or_zero(row["expected_inventory_impact"])) for row in rows if row["recommendation_type"] == "lower"))
    inventory_previous = float(sum(abs(_decimal_or_zero(row["expected_inventory_impact"])) for row in previous_rows if row["recommendation_type"] == "lower"))

    revenue_growth = _pct_change(revenue_current, revenue_previous)
    margin_growth = _pct_change(margin_current, margin_previous)
    inventory_change = _pct_change(inventory_current, inventory_previous)

    week_factors = [0.35, 0.6, 0.82, 1.0]
    points = [
        ImpactForecastPoint(
            week=f"Week {index + 1}",
            revenue=_clamp(50 + (revenue_growth * factor), 40, 120),
            margin=_clamp(50 + (margin_growth * factor), 40, 120),
            inventory=_clamp(50 + ((-inventory_change) * factor), 40, 120),
        )
        for index, factor in enumerate(week_factors)
    ]

    return ImpactForecastResponse(points=points)


def get_ai_summary(session: Session) -> AiSummary:
    rows = _fetch_recommendation_rows(session, None, None)
    executive_rows = [row for row in rows if row["recommendation_type"] in EXECUTIVE_TYPES]
    counter = Counter(row["recommendation_type"] for row in executive_rows)
    total_revenue = sum(_decimal_or_zero(row["expected_revenue_impact"]) for row in executive_rows)
    avg_margin = _average([_decimal_or_zero(row["margin_pct"]) for row in executive_rows])

    return AiSummary(
        overview=(
            f"Our pricing engine analyzed {len(executive_rows)} executive recommendations and identified "
            f"{len(executive_rows)} pricing actions with a total potential revenue uplift of "
            f"{_format_signed_currency(total_revenue)} and margin improvement of {avg_margin:.1f}%."
        ),
        bulletPoints=[
            AiSummaryBulletPoint(
                text=f"{counter.get(recommendation_type, 0)} SKUs flagged for {TYPE_TO_ACTION[recommendation_type].lower()}",
                color=TYPE_TO_COLOR[recommendation_type],
            )
            for recommendation_type in EXECUTIVE_TYPES
        ],
    )


def build_copilot_response(session: Session, message: str) -> tuple[str, list[CopilotRecommendation]]:
    rows = _fetch_recommendation_rows(session, None, None)
    ranked = sorted(rows, key=lambda row: float(_decimal_or_zero(row["expected_revenue_impact"])), reverse=True)[:3]
    reply = (
        f"Based on current PostgreSQL data, the strongest opportunities are concentrated in "
        f"{_top_categories(rows)}. Your prompt was: {message.strip() or 'no additional context provided'}."
    )
    recommendations = [
        CopilotRecommendation(
            rank=index + 1,
            recommendation=f"{TYPE_TO_ACTION[row['recommendation_type']]} for {row['sku_name']}",
            estimatedImpact=_format_signed_currency(_decimal_or_zero(row["expected_revenue_impact"])),
        )
        for index, row in enumerate(ranked)
    ]
    return reply, recommendations


def get_recommendation_inbox(
    session: Session,
    start_date: str,
    end_date: str,
    tab: str,
    q: str | None,
    confidence: str | None,
    category: str | None,
    sort_by: RecommendationSortBy,
    sort_order: RecommendationSortOrder,
) -> RecommendationInboxResponse:
    rows = _fetch_recommendation_rows(session, start_date, end_date)
    meta_rows = _filter_rows(rows, tab="all", q=q, confidence=confidence, category=category)
    filtered_rows = _filter_rows(rows, tab=tab, q=q, confidence=confidence, category=category)
    sorted_rows = _sort_rows(filtered_rows, sort_by=sort_by, sort_order=sort_order)
    counts = Counter(row["recommendation_type"] for row in meta_rows)

    return RecommendationInboxResponse(
        meta={
            "total": len(meta_rows),
            "counts": {
                "all": len(meta_rows),
                "raise": counts.get("raise", 0),
                "lower": counts.get("lower", 0),
                "promo": counts.get("promo", 0),
                "stop": counts.get("stop", 0),
            },
            "startDate": start_date,
            "endDate": end_date,
        },
        items=[_row_to_inbox_item(row) for row in sorted_rows],
    )


def get_recommendation_sku_detail(session: Session, recommendation_id: str) -> RecommendationSkuDetail | None:
    recommendation = session.exec(
        text(
            """
            SELECT
                pr.id::text AS recommendation_id,
                s.id::text AS sku_id,
                s.name AS sku_name,
                s.category AS sku_category,
                s.current_price AS current_price,
                pr.recommended_price AS recommendation_price,
                s.approval_price AS approval_price
            FROM price_recommendations pr
            JOIN skus s ON s.id = pr.sku_id
            WHERE pr.id = CAST(:recommendation_id AS uuid)
            """
        ),
        params={"recommendation_id": recommendation_id},
    ).mappings().first()

    if recommendation is None:
        return None

    history_rows = session.exec(
        text(
            """
            SELECT
                apc.recommendation_id::text AS recommendation_id,
                apc.old_price,
                apc.new_price,
                apc.applied_by,
                apc.change_reason,
                apc.applied_at
            FROM applied_price_changes apc
            WHERE apc.sku_id = CAST(:sku_id AS uuid)
            ORDER BY apc.applied_at DESC
            LIMIT 50
            """
        ),
        params={"sku_id": recommendation["sku_id"]},
    ).mappings().all()

    competitor_rows = session.exec(
        text(
            """
            WITH latest_source_prices AS (
                SELECT DISTINCT ON (cp.source)
                    cp.source,
                    cp.price,
                    cp.original_price,
                    cp.promo_price,
                    cp.currency,
                    cp.availability,
                    cp.stock_status,
                    cp.url,
                    cp.crawled_at,
                    cp.competitor_source_id,
                    cp.competitor_listing_id
                FROM competitor_prices cp
                WHERE cp.sku_id = CAST(:sku_id AS uuid)
                ORDER BY cp.source, cp.crawled_at DESC
            )
            SELECT
                lsp.source,
                cs.name AS source_name,
                cs.base_url,
                cl.competitor_sku,
                cl.competitor_product_name,
                lsp.price,
                lsp.original_price,
                lsp.promo_price,
                lsp.currency,
                lsp.availability,
                lsp.stock_status,
                lsp.url,
                lsp.crawled_at
            FROM latest_source_prices lsp
            LEFT JOIN competitor_sources cs ON cs.id = lsp.competitor_source_id
            LEFT JOIN competitor_listings cl ON cl.id = lsp.competitor_listing_id
            ORDER BY lsp.price ASC, lsp.source ASC
            """
        ),
        params={"sku_id": recommendation["sku_id"]},
    ).mappings().all()

    competitor_timeline_rows = session.exec(
        text(
            """
            SELECT
                cp.source,
                cs.name AS source_name,
                cs.base_url,
                cl.competitor_sku,
                cl.competitor_product_name,
                cp.price,
                cp.original_price,
                cp.promo_price,
                cp.currency,
                cp.availability,
                cp.stock_status,
                cp.url,
                cp.crawled_at
            FROM competitor_prices cp
            LEFT JOIN competitor_sources cs ON cs.id = cp.competitor_source_id
            LEFT JOIN competitor_listings cl ON cl.id = cp.competitor_listing_id
            WHERE cp.sku_id = CAST(:sku_id AS uuid)
            ORDER BY cp.crawled_at DESC, cp.source ASC
            LIMIT 200
            """
        ),
        params={"sku_id": recommendation["sku_id"]},
    ).mappings().all()

    return RecommendationSkuDetail(
        recommendationId=recommendation["recommendation_id"],
        skuId=recommendation["sku_id"],
        sku=recommendation["sku_name"],
        category=recommendation["sku_category"],
        currentPrice=float(recommendation["current_price"]) if recommendation["current_price"] is not None else None,
        recommendationPrice=float(recommendation["recommendation_price"]) if recommendation["recommendation_price"] is not None else None,
        approvalPrice=float(recommendation["approval_price"]) if recommendation["approval_price"] is not None else None,
        history=[
            ApprovalPriceHistoryItem(
                recommendationId=row["recommendation_id"],
                oldPrice=float(row["old_price"]) if row["old_price"] is not None else None,
                approvalPrice=float(row["new_price"]),
                actor=row["applied_by"],
                reason=row["change_reason"],
                appliedAt=row["applied_at"].isoformat(),
            )
            for row in history_rows
        ],
        competitorPrices=[
            CompetitorSourcePriceItem(
                sourceCode=row["source"],
                sourceName=row["source_name"],
                sourceWebsite=row["base_url"],
                competitorSku=row["competitor_sku"],
                competitorProductName=row["competitor_product_name"],
                price=float(row["price"]),
                originalPrice=float(row["original_price"]) if row["original_price"] is not None else None,
                promoPrice=float(row["promo_price"]) if row["promo_price"] is not None else None,
                currency=row["currency"],
                availability=row["availability"],
                stockStatus=row["stock_status"],
                url=row["url"],
                crawledAt=row["crawled_at"].isoformat(),
            )
            for row in competitor_rows
        ],
        competitorTimeline=[
            CompetitorSourcePriceItem(
                sourceCode=row["source"],
                sourceName=row["source_name"],
                sourceWebsite=row["base_url"],
                competitorSku=row["competitor_sku"],
                competitorProductName=row["competitor_product_name"],
                price=float(row["price"]),
                originalPrice=float(row["original_price"]) if row["original_price"] is not None else None,
                promoPrice=float(row["promo_price"]) if row["promo_price"] is not None else None,
                currency=row["currency"],
                availability=row["availability"],
                stockStatus=row["stock_status"],
                url=row["url"],
                crawledAt=row["crawled_at"].isoformat(),
            )
            for row in competitor_timeline_rows
        ],
    )


def decide_recommendation(session: Session, recommendation_id: str, decision: str) -> RecommendationInboxItem | None:
    normalized = decision.strip().lower()
    if normalized not in {"accept", "reject"}:
        return None

    updated = apply_approval_decision(
        session,
        recommendation_id,
        "approve" if normalized == "accept" else "reject",
        actor="dashboard-ui",
        notes=f"Recommendation {normalized}ed from recommendation inbox",
    )
    if updated is None:
        return None

    refreshed = _fetch_recommendation_by_id(session, recommendation_id)
    return _row_to_inbox_item(refreshed) if refreshed else None


def customize_recommendation(
    session: Session,
    recommendation_id: str,
    custom_price: float,
    notes: str | None = None,
    actor: str = "dashboard-ui",
) -> RecommendationInboxItem | None:
    updated = apply_approval_decision(
        session,
        recommendation_id,
        "custom",
        actor=actor,
        notes=notes,
        custom_price=custom_price,
    )
    if updated is None:
        return None

    refreshed = _fetch_recommendation_by_id(session, recommendation_id)
    return _row_to_inbox_item(refreshed) if refreshed else None


def decide_all_recommendations(
    session: Session,
    decision: str,
    tab: str,
    q: str | None,
    confidence: str | None,
    category: str | None,
) -> list[RecommendationInboxItem] | None:
    normalized = decision.strip().lower()
    if normalized not in {"accept", "reject"}:
        return None

    rows = _fetch_recommendation_rows(session, None, None)
    matched = _filter_rows(rows, tab=tab, q=q, confidence=confidence, category=category)
    if not matched:
        return []

    decision_type = "approve" if normalized == "accept" else "reject"
    for row in matched:
        apply_approval_decision(
            session,
            row["id"],
            decision_type,
            actor="dashboard-ui",
            notes=f"Recommendation {normalized}ed from recommendation inbox",
        )

    refreshed = [_fetch_recommendation_by_id(session, row["id"]) for row in matched]
    return [_row_to_inbox_item(row) for row in refreshed if row is not None]


def check_database_connection(session: Session) -> None:
    session.exec(text("SELECT 1")).one()


def _fetch_recommendation_rows(session: Session, start_date: str | None, end_date: str | None) -> list[dict]:
    sql = """
        SELECT
            pr.id::text AS id,
            s.name AS sku_name,
            s.category AS sku_category,
            s.current_price AS sku_price,
            s.approval_price AS approval_price,
            COALESCE((pr.rule_details->>'market_price')::numeric, pc.lowest_competitor_price) AS competitor_price,
            pr.recommendation_type,
            pr.current_price,
            pr.recommended_price,
            pr.margin_pct,
            pr.expected_revenue_impact,
            pr.expected_margin_impact,
            pr.expected_inventory_impact,
            pr.confidence_label,
            pr.status,
            pr.created_at
        FROM price_recommendations pr
        JOIN skus s ON s.id = pr.sku_id
        LEFT JOIN price_comparisons pc ON pc.sku_id = s.id
    """
    params: dict[str, str] = {}
    filters: list[str] = []

    if start_date:
        filters.append("pr.created_at::date >= CAST(:start_date AS date)")
        params["start_date"] = start_date

    if end_date:
        filters.append("pr.created_at::date <= CAST(:end_date AS date)")
        params["end_date"] = end_date

    if filters:
        sql = f"{sql} WHERE {' AND '.join(filters)}"

    return [
        dict(row)
        for row in session.exec(
            text(sql),
            params=params,
        ).mappings().all()
    ]


def _fetch_recommendation_by_id(session: Session, recommendation_id: str) -> dict | None:
    sql = """
        SELECT
            pr.id::text AS id,
            s.name AS sku_name,
            s.category AS sku_category,
            s.current_price AS sku_price,
            s.approval_price AS approval_price,
            COALESCE((pr.rule_details->>'market_price')::numeric, pc.lowest_competitor_price) AS competitor_price,
            pr.recommendation_type,
            pr.current_price,
            pr.recommended_price,
            pr.margin_pct,
            pr.expected_revenue_impact,
            pr.expected_margin_impact,
            pr.expected_inventory_impact,
            pr.confidence_label,
            pr.status,
            pr.created_at
        FROM price_recommendations pr
        JOIN skus s ON s.id = pr.sku_id
        LEFT JOIN price_comparisons pc ON pc.sku_id = s.id
        WHERE pr.id = CAST(:recommendation_id AS uuid)
    """
    row = session.exec(
        text(sql),
        params={"recommendation_id": recommendation_id},
    ).mappings().first()
    return dict(row) if row else None


def _insert_decision_audit(session: Session, recommendation_id: str, db_status: str) -> None:
    action = "approved" if db_status == "approved" else "rejected"
    now = datetime.now(timezone.utc)
    session.exec(
        text(
            """
            INSERT INTO approval_log (id, recommendation_id, action, actor, notes, acted_at)
            VALUES (:id, CAST(:recommendation_id AS uuid), :action, 'dashboard-ui', :notes, :acted_at)
            """
        ),
        params={
            "id": uuid4(),
            "recommendation_id": recommendation_id,
            "action": action,
            "notes": f"Recommendation {action} from recommendation inbox",
            "acted_at": now,
        },
    )
    session.exec(
        text(
            """
            INSERT INTO recommendation_events (id, recommendation_id, event_type, actor, notes, payload, created_at)
            VALUES (
                :id,
                CAST(:recommendation_id AS uuid),
                :event_type,
                'dashboard-ui',
                :notes,
                CAST(:payload AS jsonb),
                :created_at
            )
            """
        ),
        params={
            "id": uuid4(),
            "recommendation_id": recommendation_id,
            "event_type": action,
            "notes": f"Recommendation moved to {db_status}",
            "payload": '{"channel":"frontend"}',
            "created_at": now,
        },
    )


def _filter_rows(
    rows: list[dict],
    tab: str | None,
    q: str | None,
    confidence: str | None,
    category: str | None,
) -> list[dict]:
    normalized_tab = (tab or "all").strip().lower()
    normalized_q = (q or "").strip().lower()
    normalized_confidence = (confidence or "all").strip().lower()
    normalized_category = (category or "").strip().lower()

    filtered: list[dict] = []
    for row in rows:
        recommendation_type = row["recommendation_type"]
        confidence_label = (row["confidence_label"] or "Low").lower()
        sku_name = row["sku_name"].lower()
        sku_category = row["sku_category"].lower()

        if normalized_tab != "all" and recommendation_type != normalized_tab:
            continue
        if normalized_confidence != "all" and confidence_label != normalized_confidence:
            continue
        if normalized_category and sku_category != normalized_category:
            continue
        if normalized_q and normalized_q not in sku_name and normalized_q not in sku_category:
            continue

        filtered.append(row)

    return filtered


def _sort_rows(rows: list[dict], sort_by: RecommendationSortBy, sort_order: RecommendationSortOrder) -> list[dict]:
    reverse = sort_order == "desc"
    if sort_by == "sku":
        return sorted(rows, key=lambda row: row["sku_name"].lower(), reverse=reverse)
    if sort_by == "confidence":
        return sorted(rows, key=lambda row: _confidence_rank(row["confidence_label"] or "Low"), reverse=reverse)
    return sorted(rows, key=lambda row: float(_impact_value(row)), reverse=reverse)


def _row_to_inbox_item(row: dict) -> RecommendationInboxItem:
    return RecommendationInboxItem(
        id=row["id"],
        sku=row["sku_name"],
        category=row["sku_category"],
        skuPrice=float(row["sku_price"]) if row.get("sku_price") is not None else None,
        competitorPrice=float(row["competitor_price"]) if row.get("competitor_price") is not None else None,
        approvalPrice=float(row["approval_price"]) if row.get("approval_price") is not None else None,
        recommendationType=row["recommendation_type"],
        description=_build_recommendation_description(row),
        impact30d=_build_impact_label(row),
        confidence=(row["confidence_label"] or "Low"),
        status=_db_status_to_api_status(row["status"]),
    )


def _build_recommendation_description(row: dict) -> str:
    recommendation_type = row["recommendation_type"]
    if recommendation_type == "promo":
        return "Run a promotion to improve sell-through."
    if recommendation_type == "stop":
        return "Stop promotion to protect margin."

    current_price = _decimal_or_zero(row["current_price"])
    recommended_price = _decimal_or_zero(row["recommended_price"])
    if current_price == 0:
        return "Keep current price (insufficient baseline)."

    delta_pct = ((recommended_price - current_price) / current_price) * Decimal("100")
    rounded_pct = abs(int(delta_pct.quantize(Decimal("1"))))
    if recommendation_type == "raise":
        return f"Increase selling price by about {rounded_pct}% to align with market opportunity."
    return f"Decrease selling price by about {rounded_pct}% to stay competitive and improve conversion."


def _build_impact_label(row: dict) -> str:
    recommendation_type = row["recommendation_type"]
    if recommendation_type == "lower":
        inventory_impact = abs(_decimal_or_zero(row["expected_inventory_impact"]))
        return f"Clear {int(inventory_impact)}% Inv"
    if recommendation_type == "promo":
        return f"{_format_signed_currency(_decimal_or_zero(row['expected_revenue_impact']))} Volume"
    if recommendation_type == "stop":
        return f"{_format_signed_currency(_decimal_or_zero(row['expected_margin_impact']))} Margin"
    return _format_signed_currency(_decimal_or_zero(row["expected_revenue_impact"]))


def _impact_value(row: dict) -> Decimal:
    recommendation_type = row["recommendation_type"]
    if recommendation_type == "lower":
        return abs(_decimal_or_zero(row["expected_inventory_impact"]))
    if recommendation_type == "stop":
        return _decimal_or_zero(row["expected_margin_impact"])
    return _decimal_or_zero(row["expected_revenue_impact"])


def _format_signed_currency(value: Decimal) -> str:
    sign = "+" if value >= 0 else "-"
    magnitude = abs(value)
    if magnitude >= Decimal("1000000"):
        compact = f"{(magnitude / Decimal('1000000')):.1f}M"
    elif magnitude >= Decimal("1000"):
        compact = f"{(magnitude / Decimal('1000')):.0f}K"
    else:
        compact = f"{magnitude:.0f}"
    return f"{sign}${compact}"


def _average(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal("0")) / Decimal(len(values) or 1)


def _resolve_period_window(start_date: str | None, end_date: str | None) -> dict[str, str | int]:
    today = date.today()
    parsed_start = _parse_iso_date(start_date)
    parsed_end = _parse_iso_date(end_date)

    end = parsed_end or today
    start = parsed_start or (end - timedelta(days=7))
    if start > end:
        start, end = end, start

    days = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "previousStart": previous_start.isoformat(),
        "previousEnd": previous_end.isoformat(),
        "days": days,
    }


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        if current == 0:
            return 0.0
        return 100.0
    return round(((current - previous) / abs(previous)) * 100, 1)


def _count_active_strategy_runs(session: Session, start_date: str, end_date: str) -> int:
    return session.exec(
        text(
            """
            SELECT COUNT(DISTINCT sr.strategy_id)
            FROM strategy_runs sr
            JOIN strategies s ON s.id = sr.strategy_id
            WHERE s.status = 'active'
              AND s.is_active = TRUE
              AND sr.run_started_at::date >= CAST(:start_date AS date)
              AND sr.run_started_at::date <= CAST(:end_date AS date)
            """
        ),
        params={"start_date": start_date, "end_date": end_date},
    ).one()[0]


def _clamp(value: float, low: float, high: float) -> float:
    return round(max(low, min(high, value)), 1)


def _decimal_or_zero(value: Decimal | float | int | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _confidence_rank(label: str) -> int:
    return {"High": 3, "Medium": 2, "Low": 1}.get(label, 0)


def _db_status_to_api_status(status: str) -> str:
    if status in {"approved", "applied"}:
        return "accepted"
    if status == "rejected":
        return "rejected"
    return "pending"


def _decision_to_db_status(decision: str) -> str | None:
    normalized = decision.strip().lower()
    if normalized == "accept":
        return "approved"
    if normalized == "reject":
        return "rejected"
    return None


def _top_categories(rows: list[dict]) -> str:
    counter = Counter(row["sku_category"] for row in rows)
    return ", ".join(category for category, _ in counter.most_common(2)) or "the current assortment"