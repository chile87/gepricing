from __future__ import annotations

from engine.types import PricingCandidate, PricingDecision


class CompetitorRule:
	"""Generate a raise/lower signal when competitor market price deviates materially."""

	def __init__(self, raise_threshold: float = 1.03, lower_threshold: float = 0.98) -> None:
		self.raise_threshold = raise_threshold
		self.lower_threshold = lower_threshold

	def evaluate(self, candidate: PricingCandidate) -> PricingDecision | None:
		if candidate.market_price is None or candidate.current_price <= 0:
			return None

		if candidate.market_price <= candidate.current_price * self.lower_threshold:
			recommended_price = max(candidate.cost_price * 1.05, candidate.market_price * 0.995)
			return PricingDecision(
				recommendation_type="lower",
				recommended_price=recommended_price,
				confidence_score=0.82,
				confidence_label="High",
				method="market-gap",
				rationale=["Competitor market price is below current price."],
				details={
					"market_price": candidate.market_price,
					"avg_market_price": candidate.avg_market_price,
					"competitor_count": candidate.competitor_count,
					"threshold": self.lower_threshold,
				},
			)

		if candidate.market_price >= candidate.current_price * self.raise_threshold:
			recommended_price = min(candidate.market_price * 0.99, candidate.current_price * 1.08)
			return PricingDecision(
				recommendation_type="raise",
				recommended_price=recommended_price,
				confidence_score=0.76,
				confidence_label="Medium",
				method="market-gap",
				rationale=["Competitor market price is above current price."],
				details={
					"market_price": candidate.market_price,
					"avg_market_price": candidate.avg_market_price,
					"competitor_count": candidate.competitor_count,
					"threshold": self.raise_threshold,
				},
			)

		return None
