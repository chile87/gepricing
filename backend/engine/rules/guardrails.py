from __future__ import annotations

from engine.types import PricingCandidate, PricingDecision


class GuardrailsEngine:
	"""Final protection layer for extreme price moves and loss-making proposals."""

	def __init__(self, max_raise_pct: float = 0.08, max_lower_pct: float = 0.08) -> None:
		self.max_raise_pct = max_raise_pct
		self.max_lower_pct = max_lower_pct

	def apply(self, candidate: PricingCandidate, decision: PricingDecision) -> PricingDecision | None:
		if decision.recommended_price <= 0:
			return None

		min_price = candidate.current_price * (1 - self.max_lower_pct)
		max_price = candidate.current_price * (1 + self.max_raise_pct)
		clamped = min(max(decision.recommended_price, min_price), max_price)

		if clamped != decision.recommended_price:
			decision.rationale.append("Guardrail clamped the price movement.")
			decision.details["guardrail_bounds"] = {"min": min_price, "max": max_price}
			decision.recommended_price = clamped

		if decision.recommended_price <= candidate.cost_price:
			return None

		return decision
