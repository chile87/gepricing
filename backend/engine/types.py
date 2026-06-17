from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PricingCandidate:
    sku_id: str
    sku_code: str
    sku_name: str
    category: str
    brand: str | None
    currency: str
    current_price: float
    cost_price: float
    inventory: int
    reorder_point: int
    market_price: float | None
    avg_market_price: float | None
    competitor_count: int


@dataclass(slots=True)
class PricingDecision:
    recommendation_type: str | None
    recommended_price: float
    confidence_score: float
    confidence_label: str
    method: str
    rationale: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)