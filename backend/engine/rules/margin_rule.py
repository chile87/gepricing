from __future__ import annotations

from engine.types import PricingCandidate, PricingDecision


class MarginRule:
	"""Clamp recommendation so it respects a minimum category margin floor."""

	def __init__(self, category_floors: dict[str, float] | None = None, default_floor: float = 0.10) -> None:
		self.category_floors = category_floors or {"mobile": 0.12}
		self.default_floor = default_floor

	def apply(self, candidate: PricingCandidate, decision: PricingDecision) -> PricingDecision:
		floor = self.category_floors.get(candidate.category.lower(), self.default_floor)
		min_allowed_price = candidate.cost_price * (1 + floor)

		if decision.recommended_price >= min_allowed_price:
			return decision

		decision.recommended_price = min_allowed_price
		decision.rationale.append("Margin floor adjusted the proposed price.")
		decision.details["margin_floor"] = floor
		decision.details["min_allowed_price"] = min_allowed_price
		if decision.confidence_label == "High":
			decision.confidence_label = "Medium"
			decision.confidence_score = min(decision.confidence_score, 0.74)
		return decision
