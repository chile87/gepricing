from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from shared.models.dashboard import (
    AiSummary,
    CopilotRecommendation,
    KpiMetrics,
    PricingOpportunity,
)

router = APIRouter(tags=["dashboard"])


class CopilotChatRequest(BaseModel):
    message: str


class CopilotChatResponse(BaseModel):
    reply: str
    recommendations: list[CopilotRecommendation]


MOCK_KPIS = KpiMetrics(
    revenueOpportunity={
        "title": "Revenue Opportunity",
        "displayValue": "+$1.5M",
        "numericValue": 1500000,
        "change": {
            "percentage": 8.7,
            "isPositive": True,
            "periodLabel": "vs last week",
        },
    },
    marginOpportunity={
        "title": "Margin Opportunity",
        "displayValue": "+3.8%",
        "numericValue": 3.8,
        "change": {
            "percentage": 2.1,
            "isPositive": True,
            "periodLabel": "vs last week",
        },
    },
    promoWasteSaving={
        "title": "Promo Waste Saving",
        "displayValue": "+$420K",
        "numericValue": 420000,
        "change": {
            "percentage": 12.3,
            "isPositive": True,
            "periodLabel": "vs last week",
        },
    },
    overstockRisk={
        "title": "Overstock Risk",
        "displayValue": "124",
        "numericValue": 124,
        "unit": "SKUs",
        "change": {
            "percentage": 18,
            "isPositive": False,
            "periodLabel": "vs last week",
        },
    },
    activeStrategies={
        "title": "Active Strategies",
        "displayValue": "12",
        "numericValue": 12,
        "change": {
            "value": 2,
            "isPositive": True,
            "periodLabel": "vs last week",
        },
    },
)

MOCK_OPPORTUNITIES: list[PricingOpportunity] = [
    PricingOpportunity(action="Raise Price", skuCount=47, percentage=32),
    PricingOpportunity(action="Lower Price", skuCount=38, percentage=27),
    PricingOpportunity(action="Promotional Action", skuCount=34, percentage=24),
    PricingOpportunity(action="Stop Promotion", skuCount=24, percentage=17),
]

MOCK_AI_SUMMARY = AiSummary(
    overview=(
        "Our AI engine analyzed 8,352 SKUs and identified 143 pricing actions "
        "with a total potential revenue uplift of $1.2M and margin improvement of 3.8%."
    ),
    bulletPoints=[
        {"text": "47 SKUs can increase price with low elasticity", "color": "#4d7fff"},
        {"text": "38 SKUs need price reduction to clear inventory", "color": "#22c8a0"},
        {"text": "34 SKUs need targeted promotion", "color": "#f5a623"},
        {"text": "24 SKU promotions are not performing", "color": "#e879c7"},
    ],
)

MOCK_COPILOT_RECOMMENDATIONS: list[CopilotRecommendation] = [
    CopilotRecommendation(
        rank=1,
        recommendation="Increase price for 24 low-elasticity SKUs",
        estimatedImpact="$180K",
    ),
    CopilotRecommendation(
        rank=2,
        recommendation="Stop promotion on 18 low-ROI SKUs",
        estimatedImpact="$62K",
    ),
    CopilotRecommendation(
        rank=3,
        recommendation="Focus promotion on price-sensitive customers",
        estimatedImpact="$38K",
    ),
]


@router.get("/dashboard/kpis", response_model=KpiMetrics)
def get_dashboard_kpis(
    startDate: str | None = Query(default=None),
    endDate: str | None = Query(default=None),
) -> KpiMetrics:
    _ = (startDate, endDate)
    return MOCK_KPIS


@router.get("/dashboard/opportunities", response_model=list[PricingOpportunity])
def get_pricing_opportunities() -> list[PricingOpportunity]:
    return MOCK_OPPORTUNITIES


@router.get("/dashboard/summary", response_model=AiSummary)
def get_ai_summary() -> AiSummary:
    return MOCK_AI_SUMMARY


@router.post("/copilot/chat", response_model=CopilotChatResponse)
def copilot_chat(payload: CopilotChatRequest) -> CopilotChatResponse:
    _ = payload.message
    return CopilotChatResponse(
        reply="Electronics margin is mainly impacted by high promotions and low price realization.",
        recommendations=MOCK_COPILOT_RECOMMENDATIONS,
    )
