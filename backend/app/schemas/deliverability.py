"""Safe mock/local deliverability dashboard API schemas for Phase 2 P2-5."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.services.dashboard import DeliverabilityDashboardResult, MailboxDashboardResult
from app.services.deliverability import CampaignDeliverabilitySummary, DeliverabilitySummary


class DeliverabilitySummaryDTO(BaseModel):
    campaign_id: uuid.UUID | None = None
    sent: int
    blocked: int
    duplicate_denied: int
    suppressed: int
    safety_denied: int
    throttled: int
    followup_sent: int
    followup_skipped: int
    mock_bounced: int
    mock_complained: int
    mock_opened: int
    mock_replied: int
    date_from: datetime | None = None
    date_to: datetime | None = None
    mock_only: bool = True

    @classmethod
    def from_summary(
        cls, summary: DeliverabilitySummary | CampaignDeliverabilitySummary
    ) -> DeliverabilitySummaryDTO:
        campaign_id = (
            summary.campaign_id if isinstance(summary, CampaignDeliverabilitySummary) else None
        )
        return cls(
            campaign_id=campaign_id,
            sent=summary.sent,
            blocked=summary.blocked,
            duplicate_denied=summary.duplicate_denied,
            suppressed=summary.suppressed,
            safety_denied=summary.safety_denied,
            throttled=summary.throttled,
            followup_sent=summary.followup_sent,
            followup_skipped=summary.followup_skipped,
            mock_bounced=summary.mock_bounced,
            mock_complained=summary.mock_complained,
            mock_opened=summary.mock_opened,
            mock_replied=summary.mock_replied,
            date_from=summary.date_from,
            date_to=summary.date_to,
        )


class DeliverabilityResponse(BaseModel):
    deliverability: DeliverabilitySummaryDTO
    mock_only: bool = True

    @classmethod
    def from_result(cls, result: DeliverabilityDashboardResult) -> DeliverabilityResponse:
        return cls(deliverability=DeliverabilitySummaryDTO.from_summary(result.summary))


class MailboxHealthDTO(BaseModel):
    mock_domain: str
    dkim_valid: bool
    spf_valid: bool
    dmarc_valid: bool
    reputation_score: int
    mock_only: bool = True


class MailboxHealthResponse(BaseModel):
    mailbox_health: MailboxHealthDTO
    mock_only: bool = True

    @classmethod
    def from_result(cls, result: MailboxDashboardResult) -> MailboxHealthResponse:
        health = result.health
        return cls(
            mailbox_health=MailboxHealthDTO(
                mock_domain=health.mock_domain,
                dkim_valid=health.dkim_valid,
                spf_valid=health.spf_valid,
                dmarc_valid=health.dmarc_valid,
                reputation_score=health.reputation_score,
            ),
            mock_only=result.mock_only,
        )
