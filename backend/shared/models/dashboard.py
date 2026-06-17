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


RecommendationType = Literal["raise", "lower", "promo", "stop"]
RecommendationConfidence = Literal["High", "Medium", "Low"]
RecommendationStatus = Literal["pending", "accepted", "rejected"]
RecommendationDecision = Literal["accept", "reject"]
RecommendationSortBy = Literal["impact", "sku", "confidence"]
RecommendationSortOrder = Literal["asc", "desc"]


class RecommendationInboxItem(BaseModel):
    id: str
    sku: str
    category: str
    skuPrice: float | None = None
    competitorPrice: float | None = None
    recommendationType: RecommendationType
    actionLabel: str
    impact30d: str
    confidence: RecommendationConfidence
    status: RecommendationStatus = "pending"


class RecommendationInboxMeta(BaseModel):
    total: int
    counts: dict[str, int]
    startDate: str
    endDate: str


class RecommendationInboxResponse(BaseModel):
    meta: RecommendationInboxMeta
    items: list[RecommendationInboxItem]
