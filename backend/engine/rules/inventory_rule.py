from __future__ import annotations

from engine.types import PricingCandidate, PricingDecision


class InventoryRule:
	"""Fallback raise/lower signal when inventory is out of balance."""

	def evaluate(self, candidate: PricingCandidate) -> PricingDecision | None:
		if candidate.inventory >= max(candidate.reorder_point * 3, 20):
			return PricingDecision(
				recommendation_type="lower",
				recommended_price=max(candidate.cost_price * 1.05, candidate.current_price * 0.97),
				confidence_score=0.68,
				confidence_label="Medium",
				method="inventory-fallback",
				rationale=["Inventory is materially above reorder threshold."],
				details={
					"inventory": candidate.inventory,
					"reorder_point": candidate.reorder_point,
				},
			)

		if candidate.inventory <= max(int(candidate.reorder_point * 1.2), 8):
			return PricingDecision(
				recommendation_type="raise",
				recommended_price=candidate.current_price * 1.03,
				confidence_score=0.64,
				confidence_label="Medium",
				method="inventory-fallback",
				rationale=["Inventory is tight relative to reorder threshold."],
				details={
					"inventory": candidate.inventory,
					"reorder_point": candidate.reorder_point,
				},
			)

		return None
