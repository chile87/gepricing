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


class ImpactForecastPoint(BaseModel):
    week: str
    revenue: float
    margin: float
    inventory: float


class ImpactForecastResponse(BaseModel):
    points: list[ImpactForecastPoint]


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
    approvalPrice: float | None = None
    recommendationType: RecommendationType
    description: str
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


class ApprovalPriceHistoryItem(BaseModel):
    recommendationId: str | None = None
    oldPrice: float | None = None
    approvalPrice: float
    actor: str | None = None
    reason: str | None = None
    appliedAt: str


class CompetitorSourcePriceItem(BaseModel):
    sourceCode: str
    sourceName: str | None = None
    sourceWebsite: str | None = None
    competitorSku: str | None = None
    competitorProductName: str | None = None
    price: float
    originalPrice: float | None = None
    promoPrice: float | None = None
    currency: str | None = None
    availability: str | None = None
    stockStatus: str | None = None
    url: str | None = None
    crawledAt: str


class RecommendationSkuDetail(BaseModel):
    recommendationId: str
    skuId: str
    sku: str
    category: str
    currentPrice: float | None = None
    recommendationPrice: float | None = None
    approvalPrice: float | None = None
    history: list[ApprovalPriceHistoryItem]
    competitorPrices: list[CompetitorSourcePriceItem]
    competitorTimeline: list[CompetitorSourcePriceItem]
