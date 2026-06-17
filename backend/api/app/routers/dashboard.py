from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.dependencies import get_session
from app.services.dashboard_service import (
    build_copilot_response,
    customize_recommendation as customize_recommendation_service,
    decide_all_recommendations as decide_all_recommendations_service,
    decide_recommendation as decide_recommendation_service,
    get_impact_forecast as get_impact_forecast_service,
    get_ai_summary as get_ai_summary_service,
    get_dashboard_kpis as get_dashboard_kpis_service,
    get_pricing_opportunities as get_pricing_opportunities_service,
    get_recommendation_inbox as get_recommendation_inbox_service,
    get_recommendation_sku_detail as get_recommendation_sku_detail_service,
)
from shared.models.dashboard import (
    AiSummary,
    CopilotRecommendation,
    ImpactForecastResponse,
    KpiMetrics,
    PricingOpportunity,
    RecommendationInboxItem,
    RecommendationInboxResponse,
    RecommendationSkuDetail,
    RecommendationSortBy,
    RecommendationSortOrder,
    RecommendationType,
)

router = APIRouter(tags=["dashboard"])


class CopilotChatRequest(BaseModel):
    message: str


class CopilotChatResponse(BaseModel):
    reply: str
    recommendations: list[CopilotRecommendation]


class RecommendationDecisionRequest(BaseModel):
    decision: str


class BulkRecommendationDecisionRequest(BaseModel):
    decision: str
    tab: RecommendationType | str = "all"
    q: str | None = None
    confidence: str | None = None
    category: str | None = None


class CustomRecommendationRequest(BaseModel):
    customPrice: float
    notes: str | None = None
    actor: str = "dashboard-ui"


@router.get("/dashboard/kpis", response_model=KpiMetrics)
def get_dashboard_kpis(
    startDate: str | None = Query(default=None),
    endDate: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> KpiMetrics:
    return get_dashboard_kpis_service(session, startDate, endDate)


@router.get("/dashboard/impact-forecast", response_model=ImpactForecastResponse)
def get_impact_forecast(
    startDate: str | None = Query(default=None),
    endDate: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> ImpactForecastResponse:
    return get_impact_forecast_service(session, startDate, endDate)


@router.get("/dashboard/opportunities", response_model=list[PricingOpportunity])
def get_pricing_opportunities(session: Session = Depends(get_session)) -> list[PricingOpportunity]:
    return get_pricing_opportunities_service(session)


@router.get("/dashboard/summary", response_model=AiSummary)
def get_ai_summary(session: Session = Depends(get_session)) -> AiSummary:
    return get_ai_summary_service(session)


@router.post("/copilot/chat", response_model=CopilotChatResponse)
def copilot_chat(
    payload: CopilotChatRequest,
    session: Session = Depends(get_session),
) -> CopilotChatResponse:
    reply, recommendations = build_copilot_response(session, payload.message)
    return CopilotChatResponse(
        reply=reply,
        recommendations=recommendations,
    )


@router.get("/recommendations/inbox", response_model=RecommendationInboxResponse)
def get_recommendation_inbox(
    startDate: str = Query(default="2026-06-10"),
    endDate: str = Query(default="2026-06-17"),
    tab: str = Query(default="all"),
    q: str | None = Query(default=None),
    confidence: str | None = Query(default="all"),
    category: str | None = Query(default=None),
    sortBy: RecommendationSortBy = Query(default="impact"),
    sortOrder: RecommendationSortOrder = Query(default="desc"),
    session: Session = Depends(get_session),
) -> RecommendationInboxResponse:
    return get_recommendation_inbox_service(
        session=session,
        start_date=startDate,
        end_date=endDate,
        tab=tab,
        q=q,
        confidence=confidence,
        category=category,
        sort_by=sortBy,
        sort_order=sortOrder,
    )


@router.get("/recommendations/inbox/{recommendation_id}/detail", response_model=RecommendationSkuDetail)
def get_recommendation_sku_detail(
    recommendation_id: str,
    session: Session = Depends(get_session),
) -> RecommendationSkuDetail:
    detail = get_recommendation_sku_detail_service(session, recommendation_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"recommendation '{recommendation_id}' not found")
    return detail


@router.post("/recommendations/inbox/{recommendation_id}/decision", response_model=RecommendationInboxItem)
def decide_recommendation(
    recommendation_id: str,
    payload: RecommendationDecisionRequest,
    session: Session = Depends(get_session),
) -> RecommendationInboxItem:
    item = decide_recommendation_service(session, recommendation_id, payload.decision)
    if item is None:
        normalized = payload.decision.strip().lower()
        if normalized not in {"accept", "reject"}:
            raise HTTPException(status_code=400, detail="decision must be 'accept' or 'reject'")
        raise HTTPException(status_code=404, detail=f"recommendation '{recommendation_id}' not found")
    return item


@router.post("/recommendations/inbox/{recommendation_id}/custom", response_model=RecommendationInboxItem)
def customize_recommendation(
    recommendation_id: str,
    payload: CustomRecommendationRequest,
    session: Session = Depends(get_session),
) -> RecommendationInboxItem:
    item = customize_recommendation_service(
        session,
        recommendation_id,
        payload.customPrice,
        notes=payload.notes,
        actor=payload.actor,
    )
    if item is None:
        raise HTTPException(status_code=404, detail=f"recommendation '{recommendation_id}' not found")
    return item


@router.post("/recommendations/inbox/decision-all", response_model=list[RecommendationInboxItem])
def decide_all_recommendations(
    payload: BulkRecommendationDecisionRequest,
    session: Session = Depends(get_session),
) -> list[RecommendationInboxItem]:
    items = decide_all_recommendations_service(
        session=session,
        decision=payload.decision,
        tab=payload.tab,
        q=payload.q,
        confidence=payload.confidence,
        category=payload.category,
    )
    if items is None:
        raise HTTPException(status_code=400, detail="decision must be 'accept' or 'reject'")
    return items
