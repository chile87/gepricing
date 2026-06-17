from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import json
from uuid import uuid4

from sqlalchemy import text
from sqlmodel import Session

from app.services.market_data_service import (
	replace_market_data_from_file,
	replace_market_data_from_payload,
)
from engine.engine import PricingEngine
from engine.types import PricingCandidate


def replace_market_data_from_mobile_file(session: Session, file_path: str | None = None) -> dict[str, int]:
	stats = replace_market_data_from_file(session, file_path)
	refresh_price_comparisons(session)
	session.commit()
	return stats


def replace_market_data_from_records(
	session: Session,
	payload: list[dict],
	source_name: str = "api-payload",
) -> dict[str, int]:
	stats = replace_market_data_from_payload(session, payload, source_name)
	refresh_price_comparisons(session)
	session.commit()
	return stats


def ensure_price_comparisons_table(session: Session) -> None:
	session.exec(
		text(
			"""
			CREATE TABLE IF NOT EXISTS price_comparisons (
				id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
				sku_id UUID NOT NULL REFERENCES skus(id) ON DELETE CASCADE UNIQUE,
				competitor_count INTEGER NOT NULL DEFAULT 0,
				lowest_competitor_price NUMERIC(14, 2),
				average_competitor_price NUMERIC(14, 2),
				highest_competitor_price NUMERIC(14, 2),
				price_gap_value NUMERIC(14, 2),
				price_gap_pct NUMERIC(8, 2),
				lowest_competitor_source VARCHAR(64),
				snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
				created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
				updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
				CONSTRAINT chk_price_comparisons_competitor_count CHECK (competitor_count >= 0)
			)
			"""
		)
	)


def refresh_price_comparisons(session: Session, sku_ids: list[str] | None = None) -> None:
	ensure_price_comparisons_table(session)
	params: dict[str, object] = {}
	delete_sql = "DELETE FROM price_comparisons"
	filter_sql = ""

	if sku_ids:
		params["sku_ids"] = sku_ids
		delete_sql = "DELETE FROM price_comparisons WHERE sku_id = ANY(CAST(:sku_ids AS uuid[]))"
		filter_sql = "WHERE s.id = ANY(CAST(:sku_ids AS uuid[]))"

	session.exec(text(delete_sql), params=params)
	session.exec(
		text(
			f"""
			INSERT INTO price_comparisons (
				id,
				sku_id,
				competitor_count,
				lowest_competitor_price,
				average_competitor_price,
				highest_competitor_price,
				price_gap_value,
				price_gap_pct,
				lowest_competitor_source,
				snapshot_at,
				created_at,
				updated_at
			)
			WITH latest_prices AS (
				SELECT DISTINCT ON (cp.sku_id, cp.source)
					cp.sku_id,
					cp.source,
					cp.price,
					cp.crawled_at
				FROM competitor_prices cp
				ORDER BY cp.sku_id, cp.source, cp.crawled_at DESC
			), ranked_prices AS (
				SELECT
					lp.*,
					ROW_NUMBER() OVER (PARTITION BY lp.sku_id ORDER BY lp.price ASC, lp.crawled_at DESC) AS price_rank
				FROM latest_prices lp
			)
			SELECT
				uuid_generate_v4(),
				s.id,
				COUNT(rp.price)::int AS competitor_count,
				MIN(rp.price) AS lowest_competitor_price,
				AVG(rp.price) AS average_competitor_price,
				MAX(rp.price) AS highest_competitor_price,
				CASE WHEN MIN(rp.price) IS NULL THEN NULL ELSE MIN(rp.price) - s.current_price END AS price_gap_value,
				CASE
					WHEN MIN(rp.price) IS NULL OR s.current_price = 0 THEN NULL
					ELSE ((MIN(rp.price) - s.current_price) / s.current_price) * 100
				END AS price_gap_pct,
				MAX(CASE WHEN rp.price_rank = 1 THEN rp.source END) AS lowest_competitor_source,
				NOW(),
				NOW(),
				NOW()
			FROM skus s
				LEFT JOIN ranked_prices rp ON rp.sku_id = s.id
			{filter_sql}
			GROUP BY s.id, s.current_price
			"""
		),
		params=params,
	)


def build_price_comparisons(session: Session) -> list[PricingCandidate]:
	ensure_price_comparisons_table(session)
	rows = session.exec(
		text(
			"""
			SELECT
				s.id::text AS sku_id,
				s.sku_code,
				s.name AS sku_name,
				s.category,
				s.brand,
				s.currency,
				s.current_price,
				s.cost_price,
				s.inventory,
				s.reorder_point,
				pc.lowest_competitor_price AS market_price,
				pc.average_competitor_price AS avg_market_price,
				COALESCE(pc.competitor_count, 0) AS competitor_count
			FROM skus s
			LEFT JOIN price_comparisons pc ON pc.sku_id = s.id
			WHERE s.is_active = TRUE
			ORDER BY s.name
			"""
		)
	).mappings().all()

	return [
		PricingCandidate(
			sku_id=row["sku_id"],
			sku_code=row["sku_code"],
			sku_name=row["sku_name"],
			category=row["category"],
			brand=row["brand"],
			currency=row["currency"],
			current_price=float(row["current_price"]),
			cost_price=float(row["cost_price"]),
			inventory=int(row["inventory"]),
			reorder_point=int(row["reorder_point"]),
			market_price=float(row["market_price"]) if row["market_price"] is not None else None,
			avg_market_price=float(row["avg_market_price"]) if row["avg_market_price"] is not None else None,
			competitor_count=int(row["competitor_count"]),
		)
		for row in rows
	]


def generate_recommendations(session: Session, triggered_by: str = "api") -> dict[str, int | str]:
	refresh_price_comparisons(session)
	session.exec(
		text("DELETE FROM price_recommendations WHERE COALESCE(rule_details->>'source', '') = 'auto-generated'")
	)

	strategy_id = str(uuid4())
	run_id = str(uuid4())
	now = datetime.now(timezone.utc)

	session.exec(
		text(
			"""
			INSERT INTO strategies (id, name, description, status, created_by, is_active, created_at, updated_at)
			VALUES (
				:id,
				'Rule Engine Market+Inventory Strategy',
				'Flow: crawler -> importer -> postgres -> rule engine -> recommendations',
				'active',
				:created_by,
				TRUE,
				:created_at,
				:updated_at
			)
			"""
		),
		params={"id": strategy_id, "created_by": triggered_by, "created_at": now, "updated_at": now},
	)
	session.exec(
		text(
			"""
			INSERT INTO strategy_runs (
				id, strategy_id, triggered_by, status, run_started_at, run_finished_at, input_snapshot, output_summary
			) VALUES (
				:id, :strategy_id, :triggered_by, 'completed', :run_started_at, :run_finished_at,
				CAST(:input_snapshot AS jsonb), CAST(:output_summary AS jsonb)
			)
			"""
		),
		params={
			"id": run_id,
			"strategy_id": strategy_id,
			"triggered_by": triggered_by,
			"run_started_at": now,
			"run_finished_at": now,
			"input_snapshot": json.dumps({"candidate_count": 0, "flow": "crawler-import-engine"}),
			"output_summary": json.dumps({}),
		},
	)

	engine = PricingEngine()
	comparisons = build_price_comparisons(session)
	inserted = 0
	counts: Counter[str] = Counter()

	for candidate in comparisons:
		decision = engine.recommend(candidate)
		if decision is None or decision.recommendation_type is None:
			continue

		delta = decision.recommended_price - candidate.current_price
		expected_revenue_impact = delta * max(candidate.inventory, 1) * 0.35
		expected_margin_impact = (decision.recommended_price - candidate.cost_price) * max(candidate.inventory, 1) * 0.22
		expected_inventory_impact = (8 + abs(delta / candidate.current_price) * 100) if decision.recommendation_type == "lower" else -(4 + abs(delta / candidate.current_price) * 40)
		margin_pct = ((decision.recommended_price - candidate.cost_price) / max(decision.recommended_price, 1)) * 100

		rule_details = dict(decision.details)
		rule_details.update({"source": "auto-generated", "sku_code": candidate.sku_code})
		session.exec(
			text(
				"""
				INSERT INTO price_recommendations (
					id, strategy_run_id, strategy_id, sku_id, recommendation_type, current_price,
					recommended_price, margin_pct, expected_revenue_impact, expected_margin_impact,
					expected_inventory_impact, confidence_score, confidence_label, rule_details,
					rationale, status, created_at, updated_at
				) VALUES (
					:id, :strategy_run_id, :strategy_id, CAST(:sku_id AS uuid), :recommendation_type, :current_price,
					:recommended_price, :margin_pct, :expected_revenue_impact, :expected_margin_impact,
					:expected_inventory_impact, :confidence_score, :confidence_label, CAST(:rule_details AS jsonb),
					CAST(:rationale AS jsonb), 'pending', :created_at, :updated_at
				)
				"""
			),
			params={
				"id": str(uuid4()),
				"strategy_run_id": run_id,
				"strategy_id": strategy_id,
				"sku_id": candidate.sku_id,
				"recommendation_type": decision.recommendation_type,
				"current_price": round(candidate.current_price, 2),
				"recommended_price": round(decision.recommended_price, 2),
				"margin_pct": round(margin_pct, 2),
				"expected_revenue_impact": round(expected_revenue_impact, 2),
				"expected_margin_impact": round(expected_margin_impact, 2),
				"expected_inventory_impact": round(expected_inventory_impact, 2),
				"confidence_score": round(decision.confidence_score, 2),
				"confidence_label": decision.confidence_label,
				"rule_details": json.dumps(rule_details),
				"rationale": json.dumps({"steps": decision.rationale, "method": decision.method}),
				"created_at": now,
				"updated_at": now,
			},
		)
		inserted += 1
		counts[decision.recommendation_type] += 1

	session.exec(
		text(
			"""
			UPDATE strategy_runs
			SET input_snapshot = CAST(:input_snapshot AS jsonb),
				output_summary = CAST(:output_summary AS jsonb)
			WHERE id = CAST(:run_id AS uuid)
			"""
		),
		params={
			"run_id": run_id,
			"input_snapshot": json.dumps({"candidate_count": len(comparisons), "flow": "crawler-import-engine"}),
			"output_summary": json.dumps({"inserted": inserted, "counts": dict(counts)}),
		},
	)
	session.commit()
	return {"strategyId": strategy_id, "strategyRunId": run_id, "inserted": inserted, "raise": counts.get("raise", 0), "lower": counts.get("lower", 0)}


def list_recommendations(session: Session, status: str | None = None, sku_code: str | None = None) -> list[dict]:
	sql = """
		SELECT
			pr.id::text AS id,
			s.id::text AS sku_id,
			s.sku_code,
			s.name AS sku_name,
			s.category,
			pr.recommendation_type,
			pr.current_price,
			pr.recommended_price,
			pr.margin_pct,
			pr.confidence_score,
			pr.confidence_label,
			pr.status,
			pr.rule_details,
			pr.rationale,
			pr.created_at
		FROM price_recommendations pr
		JOIN skus s ON s.id = pr.sku_id
	"""
	filters: list[str] = []
	params: dict[str, str] = {}
	if status:
		filters.append("pr.status = :status")
		params["status"] = status
	if sku_code:
		filters.append("s.sku_code = :sku_code")
		params["sku_code"] = sku_code
	if filters:
		sql = f"{sql} WHERE {' AND '.join(filters)}"
	sql = f"{sql} ORDER BY pr.created_at DESC"
	return [dict(row) for row in session.exec(text(sql), params=params).mappings().all()]


def get_recommendation(session: Session, recommendation_id: str) -> dict | None:
	rows = session.exec(
		text(
			"""
			SELECT
				pr.id::text AS id,
				s.id::text AS sku_id,
				s.sku_code,
				s.name AS sku_name,
				s.category,
				pr.recommendation_type,
				pr.current_price,
				pr.recommended_price,
				pr.margin_pct,
				pr.confidence_score,
				pr.confidence_label,
				pr.status,
				pr.rule_details,
				pr.rationale,
				pr.created_at
			FROM price_recommendations pr
			JOIN skus s ON s.id = pr.sku_id
			WHERE pr.id = CAST(:recommendation_id AS uuid)
			"""
		),
		params={"recommendation_id": recommendation_id},
	).mappings().first()
	return dict(rows) if rows else None


def list_pending_approvals(session: Session) -> list[dict]:
	return list_recommendations(session, status="pending")


def apply_approval_decision(
	session: Session,
	recommendation_id: str,
	decision: str,
	actor: str = "api",
	notes: str | None = None,
	custom_price: float | None = None,
) -> dict | None:
	recommendation = get_recommendation(session, recommendation_id)
	if recommendation is None:
		return None

	now = datetime.now(timezone.utc)
	if decision == "reject":
		session.exec(
			text("UPDATE price_recommendations SET status = 'rejected', updated_at = :updated_at WHERE id = CAST(:id AS uuid)"),
			params={"id": recommendation_id, "updated_at": now},
		)
		_insert_approval_log(session, recommendation_id, "rejected", actor, notes or "Recommendation rejected", now)
		_insert_recommendation_event(session, recommendation_id, "rejected", actor, notes or "Recommendation rejected", {"decision": "reject"}, now)
		session.commit()
		return get_recommendation(session, recommendation_id)

	applied_price = custom_price if custom_price is not None else float(recommendation["recommended_price"])
	session.exec(
		text(
			"""
			UPDATE price_recommendations
			SET status = 'applied', recommended_price = :recommended_price, updated_at = :updated_at
			WHERE id = CAST(:id AS uuid)
			"""
		),
		params={"id": recommendation_id, "recommended_price": applied_price, "updated_at": now},
	)
	session.exec(
		text(
			"UPDATE skus SET current_price = :current_price, updated_at = :updated_at WHERE id = CAST(:sku_id AS uuid)"
		),
		params={"sku_id": recommendation["sku_id"], "current_price": applied_price, "updated_at": now},
	)
	_insert_approval_log(session, recommendation_id, "approved", actor, notes or "Recommendation approved", now)
	_insert_recommendation_event(
		session,
		recommendation_id,
		"approved",
		actor,
		notes or "Recommendation approved",
		{"decision": decision, "applied_price": applied_price},
		now,
	)
	session.exec(
		text(
			"""
			INSERT INTO applied_price_changes (
				id, recommendation_id, sku_id, old_price, new_price, applied_by, applied_at, change_reason
			) VALUES (
				:id, CAST(:recommendation_id AS uuid), CAST(:sku_id AS uuid), :old_price, :new_price, :applied_by, :applied_at, :change_reason
			)
			"""
		),
		params={
			"id": str(uuid4()),
			"recommendation_id": recommendation_id,
			"sku_id": recommendation["sku_id"],
			"old_price": recommendation["current_price"],
			"new_price": applied_price,
			"applied_by": actor,
			"applied_at": now,
			"change_reason": notes or ("Custom price override" if custom_price is not None else "Approved recommendation"),
		},
	)
	refresh_price_comparisons(session, [recommendation["sku_id"]])
	session.commit()
	return get_recommendation(session, recommendation_id)


def _insert_approval_log(session: Session, recommendation_id: str, action: str, actor: str, notes: str, acted_at: datetime) -> None:
	session.exec(
		text(
			"""
			INSERT INTO approval_log (id, recommendation_id, action, actor, notes, acted_at)
			VALUES (:id, CAST(:recommendation_id AS uuid), :action, :actor, :notes, :acted_at)
			"""
		),
		params={
			"id": str(uuid4()),
			"recommendation_id": recommendation_id,
			"action": action,
			"actor": actor,
			"notes": notes,
			"acted_at": acted_at,
		},
	)


def _insert_recommendation_event(
	session: Session,
	recommendation_id: str,
	event_type: str,
	actor: str,
	notes: str,
	payload: dict,
	created_at: datetime,
) -> None:
	session.exec(
		text(
			"""
			INSERT INTO recommendation_events (id, recommendation_id, event_type, actor, notes, payload, created_at)
			VALUES (:id, CAST(:recommendation_id AS uuid), :event_type, :actor, :notes, CAST(:payload AS jsonb), :created_at)
			"""
		),
		params={
			"id": str(uuid4()),
			"recommendation_id": recommendation_id,
			"event_type": event_type,
			"actor": actor,
			"notes": notes,
			"payload": json.dumps(payload),
			"created_at": created_at,
		},
	)
