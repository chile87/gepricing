from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.dependencies import get_session
from app.services.pricing_service import (
	generate_recommendations,
	get_comparison_result_insights,
	get_recommendation,
	list_recommendations,
	replace_market_data_from_comparison_json_file,
	replace_market_data_from_comparison_records,
	replace_market_data_from_records,
	replace_market_data_from_mobile_file,
)

router = APIRouter(tags=["pricing"])


class ImportMobileDataRequest(BaseModel):
	filePath: str | None = None
	payload: list[dict] | None = None


class ImportComparisonDataRequest(BaseModel):
	filePath: str | None = None
	payload: list[dict] | None = None


class GenerateRecommendationsRequest(BaseModel):
	triggeredBy: str = "api"


@router.post("/pricing/import-mobile-data")
def import_mobile_data(
	payload: ImportMobileDataRequest,
	session: Session = Depends(get_session),
) -> dict[str, int]:
	if payload.payload is not None:
		return replace_market_data_from_records(session, payload.payload, "api-payload")
	return replace_market_data_from_mobile_file(session, payload.filePath)


@router.post("/pricing/import-comparison-data")
def import_comparison_data(
	payload: ImportComparisonDataRequest,
	session: Session = Depends(get_session),
) -> dict[str, int]:
	if payload.payload is not None:
		return replace_market_data_from_comparison_records(session, payload.payload, "comparison-api-payload")
	return replace_market_data_from_comparison_json_file(session, payload.filePath)


@router.post("/pricing/generate")
def generate_pricing_recommendations(
	payload: GenerateRecommendationsRequest,
	session: Session = Depends(get_session),
) -> dict[str, int | str]:
	return generate_recommendations(session, payload.triggeredBy)


@router.post("/pricing/pipeline/mobile")
def run_mobile_pipeline(
	payload: ImportMobileDataRequest,
	session: Session = Depends(get_session),
) -> dict[str, object]:
	if payload.payload is not None:
		imported = replace_market_data_from_records(session, payload.payload, "pipeline-payload")
	else:
		imported = replace_market_data_from_mobile_file(session, payload.filePath)
	generated = generate_recommendations(session, triggered_by="pipeline")
	return {"imported": imported, "generated": generated}


@router.get("/pricing/recommendations")
def get_pricing_recommendations(
	status: str | None = Query(default=None),
	skuCode: str | None = Query(default=None),
	session: Session = Depends(get_session),
) -> list[dict]:
	return list_recommendations(session, status=status, sku_code=skuCode)


@router.get("/pricing/recommendations/{recommendation_id}")
def get_pricing_recommendation(recommendation_id: str, session: Session = Depends(get_session)) -> dict | None:
	return get_recommendation(session, recommendation_id)


@router.get("/pricing/comparison-insights")
def get_pricing_comparison_insights(
	filePath: str | None = Query(default=None),
	minConfidence: float | None = Query(default=None),
	matchType: str | None = Query(default=None),
	q: str | None = Query(default=None),
	limit: int = Query(default=100, ge=1, le=500),
	offset: int = Query(default=0, ge=0),
) -> dict:
	return get_comparison_result_insights(
		file_path=filePath,
		min_confidence=minConfidence,
		match_type=matchType,
		q=q,
		limit=limit,
		offset=offset,
	)
