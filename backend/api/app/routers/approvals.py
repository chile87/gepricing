from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.dependencies import get_session
from app.services.pricing_service import (
	apply_approval_decision,
	list_pending_approvals,
	reset_approval_prices,
)

router = APIRouter(tags=["approvals"])


class ApprovalRequest(BaseModel):
	actor: str = "admin"
	notes: str | None = None
	customPrice: float | None = None


class ResetApprovalPriceRequest(BaseModel):
	skuIds: list[str] | None = None


@router.get("/approvals/pending")
def get_pending_approvals(session: Session = Depends(get_session)) -> list[dict]:
	return list_pending_approvals(session)


@router.post("/approvals/{recommendation_id}/approve")
def approve_recommendation(
	recommendation_id: str,
	payload: ApprovalRequest,
	session: Session = Depends(get_session),
) -> dict:
	item = apply_approval_decision(session, recommendation_id, "approve", payload.actor, payload.notes)
	if item is None:
		raise HTTPException(status_code=404, detail="recommendation not found")
	return item


@router.post("/approvals/{recommendation_id}/reject")
def reject_recommendation(
	recommendation_id: str,
	payload: ApprovalRequest,
	session: Session = Depends(get_session),
) -> dict:
	item = apply_approval_decision(session, recommendation_id, "reject", payload.actor, payload.notes)
	if item is None:
		raise HTTPException(status_code=404, detail="recommendation not found")
	return item


@router.post("/approvals/{recommendation_id}/custom")
def custom_price_approval(
	recommendation_id: str,
	payload: ApprovalRequest,
	session: Session = Depends(get_session),
) -> dict:
	if payload.customPrice is None:
		raise HTTPException(status_code=400, detail="customPrice is required")
	item = apply_approval_decision(
		session,
		recommendation_id,
		"custom",
		payload.actor,
		payload.notes,
		custom_price=payload.customPrice,
	)
	if item is None:
		raise HTTPException(status_code=404, detail="recommendation not found")
	return item


@router.post("/approvals/reset-approval-price")
def reset_sku_approval_price(
	payload: ResetApprovalPriceRequest,
	session: Session = Depends(get_session),
) -> dict[str, int]:
	return reset_approval_prices(session, payload.skuIds)
