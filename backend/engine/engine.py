from __future__ import annotations

from engine.rules.competitor_rule import CompetitorRule
from engine.rules.guardrails import GuardrailsEngine
from engine.rules.inventory_rule import InventoryRule
from engine.rules.margin_rule import MarginRule
from engine.types import PricingCandidate, PricingDecision


class PricingEngine:
	"""Orchestrates competitor, inventory, margin, and guardrail rules."""

	def __init__(self) -> None:
		self.competitor_rule = CompetitorRule()
		self.inventory_rule = InventoryRule()
		self.margin_rule = MarginRule()
		self.guardrails = GuardrailsEngine()

	def recommend(self, candidate: PricingCandidate) -> PricingDecision | None:
		decision = self.competitor_rule.evaluate(candidate)
		if decision is None:
			decision = self.inventory_rule.evaluate(candidate)
		if decision is None or decision.recommendation_type is None:
			return None

		decision = self.margin_rule.apply(candidate, decision)
		return self.guardrails.apply(candidate, decision)
