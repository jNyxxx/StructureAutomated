"""Safe mock/local outcomes and ROI dashboard API schemas for Phase 2 P2-5."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.repositories.outcomes_repo import OutcomeEventRecord
from app.services.dashboard import (
    MockOutcomeEventResult,
    OutcomesDashboardResult,
    ROIDashboardResult,
)
from app.services.outcomes import CampaignOutcomesSummary, OutcomesSummary


class OutcomesSummaryDTO(BaseModel):
    campaign_id: uuid.UUID | None = None
    reply_count: int
    positive_reply_count: int
    meeting_booked_count: int
    opportunity_count: int
    deal_won_count: int
    deal_lost_count: int
    unsubscribe_count: int
    bounce_count: int
    complaint_count: int
    reply_rate: float
    positive_reply_rate: float
    meeting_rate: float
    opportunity_rate: float
    win_rate: float
    date_from: datetime | None = None
    date_to: datetime | None = None
    mock_only: bool = True

    @classmethod
    def from_summary(cls, summary: OutcomesSummary | CampaignOutcomesSummary) -> OutcomesSummaryDTO:
        campaign_id = summary.campaign_id if isinstance(summary, CampaignOutcomesSummary) else None
        return cls(
            campaign_id=campaign_id,
            reply_count=summary.reply_count,
            positive_reply_count=summary.positive_reply_count,
            meeting_booked_count=summary.meeting_booked_count,
            opportunity_count=summary.opportunity_count,
            deal_won_count=summary.deal_won_count,
            deal_lost_count=summary.deal_lost_count,
            unsubscribe_count=summary.unsubscribe_count,
            bounce_count=summary.bounce_count,
            complaint_count=summary.complaint_count,
            reply_rate=summary.reply_rate,
            positive_reply_rate=summary.positive_reply_rate,
            meeting_rate=summary.meeting_rate,
            opportunity_rate=summary.opportunity_rate,
            win_rate=summary.win_rate,
            date_from=summary.date_from,
            date_to=summary.date_to,
        )


class OutcomesResponse(BaseModel):
    outcomes: OutcomesSummaryDTO
    mock_only: bool = True

    @classmethod
    def from_result(cls, result: OutcomesDashboardResult) -> OutcomesResponse:
        return cls(outcomes=OutcomesSummaryDTO.from_summary(result.summary))


class ROISummaryDTO(BaseModel):
    campaign_id: uuid.UUID
    sent_count: int
    estimated_cost_cents: int
    estimated_pipeline_value_cents: int
    estimated_won_value_cents: int
    estimated_roi_percent: float | None = None
    mock_only: bool = True


class ROIResponse(BaseModel):
    roi: ROISummaryDTO
    mock_only: bool = True

    @classmethod
    def from_result(cls, result: ROIDashboardResult) -> ROIResponse:
        summary = result.summary
        return cls(
            roi=ROISummaryDTO(
                campaign_id=summary.campaign_id,
                sent_count=summary.sent_count,
                estimated_cost_cents=summary.estimated_cost_cents,
                estimated_pipeline_value_cents=summary.estimated_pipeline_value_cents,
                estimated_won_value_cents=summary.estimated_won_value_cents,
                estimated_roi_percent=summary.estimated_roi_percent,
            ),
            mock_only=result.mock_only,
        )


class MockOutcomeEventRequest(BaseModel):
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    event_type: str
    outbound_message_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=500)
    occurred_at: datetime | None = None


class MockOutcomeEventDTO(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    contact_id: uuid.UUID
    outbound_message_id: uuid.UUID | None = None
    event_type: str
    note: str | None = None
    occurred_at: datetime
    created_at: datetime
    mock_only: bool = True

    @classmethod
    def from_record(cls, record: OutcomeEventRecord) -> MockOutcomeEventDTO:
        return cls(
            id=record.id,
            campaign_id=record.campaign_id,
            contact_id=record.contact_id,
            outbound_message_id=record.outbound_message_id,
            event_type=record.event_type,
            note=record.note,
            occurred_at=record.occurred_at,
            created_at=record.created_at,
        )


class MockOutcomeEventResponse(BaseModel):
    outcome_event: MockOutcomeEventDTO
    mock_only: bool = True

    @classmethod
    def from_result(cls, result: MockOutcomeEventResult) -> MockOutcomeEventResponse:
        return cls(
            outcome_event=MockOutcomeEventDTO.from_record(result.event),
            mock_only=result.mock_only,
        )
