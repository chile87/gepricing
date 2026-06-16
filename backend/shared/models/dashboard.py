from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class MetricChange(BaseModel):
    value: float | None = None
    percentage: float | None = None
    isPositive: bool
    periodLabel: str | None = None


class KpiMetricItem(BaseModel):
    title: str
    displayValue: str
    numericValue: float | None = None
    unit: str | None = None
    change: MetricChange


class KpiMetrics(BaseModel):
    revenueOpportunity: KpiMetricItem
    marginOpportunity: KpiMetricItem
    promoWasteSaving: KpiMetricItem
    overstockRisk: KpiMetricItem
    activeStrategies: KpiMetricItem


PricingOpportunityAction = Literal[
    "Raise Price",
    "Lower Price",
    "Promotional Action",
    "Stop Promotion",
]


class PricingOpportunity(BaseModel):
    action: PricingOpportunityAction
    skuCount: int
    percentage: int


class AiSummaryBulletPoint(BaseModel):
    text: str
    color: str | None = None


class AiSummary(BaseModel):
    overview: str
    bulletPoints: list[AiSummaryBulletPoint]


class CopilotRecommendation(BaseModel):
    rank: int
    recommendation: str
    estimatedImpact: str
