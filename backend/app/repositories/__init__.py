"""Repositories: tenant-scoped SQL only, executed via the tenant DB helper."""

from app.repositories.deliverability_repo import (
    DeliverabilityRepository,
    DeliverabilityTrendPoint,
    FollowupCounts,
    GateCounts,
    OutboundCounts,
)
from app.repositories.draft_repo import DraftRepository
from app.repositories.followup_repo import (
    FollowUpRepository,
    FollowUpRuleRecord,
    FollowUpScheduleRecord,
)
from app.repositories.knowledge_repo import KnowledgeRepository
from app.repositories.outcomes_repo import (
    OutcomeEventRecord,
    OutcomesRepository,
    OutcomeTrendPoint,
    OutcomeTypeCounts,
    ROIAssumptionsRecord,
)
from app.repositories.research_repo import ResearchRepository
from app.repositories.review_repo import ReviewRecord, ReviewRepository
from app.repositories.safety_repo import SafetyRepository
from app.repositories.sending_repo import (
    OutboundMessageRecord,
    SendGateResultRecord,
    SendingRepository,
)

__all__ = [
    "DeliverabilityRepository",
    "DeliverabilityTrendPoint",
    "FollowupCounts",
    "GateCounts",
    "OutboundCounts",
    "DraftRepository",
    "KnowledgeRepository",
    "OutcomeEventRecord",
    "OutcomeTrendPoint",
    "OutcomeTypeCounts",
    "OutcomesRepository",
    "ROIAssumptionsRecord",
    "ResearchRepository",
    "SafetyRepository",
    "ReviewRepository",
    "ReviewRecord",
    "SendingRepository",
    "SendGateResultRecord",
    "OutboundMessageRecord",
    "FollowUpRepository",
    "FollowUpRuleRecord",
    "FollowUpScheduleRecord",
]
