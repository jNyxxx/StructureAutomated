"""LOCAL/MOCK-ONLY deterministic grounding seed for the Docker E2E happy path.

Ingests one clearly-labeled mock knowledge document through the existing gated
``RAGGroundingService.add_document`` path (RBAC + audit preserved) so local
draft generation has at least one active knowledge chunk to ground against.
No gate is weakened: the seeded content still has to pass the real safety and
groundedness checks like any other tenant-authored knowledge document.

Refuses to run unless ``APP_ENV`` is local/development/demo. Never imported by
a request-handling path — invoke as ``python -m app.scripts.seed_local_grounding``.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.audit.repository import AuditRepository
from app.audit.service import AuditService
from app.auth.principal import CurrentPrincipal
from app.config import Settings, get_settings
from app.database import tenant_session
from app.repositories.billing_repo import BillingRepository
from app.repositories.campaign_repo import CampaignRepository
from app.repositories.compliance_repo import ComplianceRepository
from app.repositories.contact_repo import ContactReadRepository
from app.repositories.knowledge_repo import KnowledgeRepository
from app.services.authz import ObjectAuthorizationService, RBACService
from app.services.billing import BillingGateService
from app.services.compliance import ComplianceGateService
from app.services.rag_grounding import RAGGroundingService

_ALLOWED_SEED_ENVS = frozenset({"local", "development", "demo"})

# Demo tenant/user provisioned by the P3-2 local DB seed (docs/evidence/phase-3-2-live-db-smoke.md).
DEFAULT_TENANT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
_LOCAL_MOCK_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_LOCAL_MOCK_PROVIDER_USER_ID = "local_mock_user"
_LOCAL_MOCK_PROVIDER_SESSION_REF = "local_mock_session_ref"
_LOCAL_MOCK_EMAIL = "owner@example.com"

SEED_DOC_TITLE = "LOCAL DEMO MOCK - CRE Outreach Grounding Guidelines"
SEED_DOC_CONTENT = (
    "LOCAL DEMO MOCK: This document provides deterministic brand-voice and "
    "acquisition-strategy guidance for commercial real estate outreach drafts "
    "generated in local development and demo environments only.\n\n"
    "LOCAL DEMO MOCK: Outreach should reference the target company's likely "
    "asset focus, such as triple net lease, industrial, or multifamily "
    "properties, and open with a concise, professional introduction that "
    "respects the recipient's time.\n\n"
    "LOCAL DEMO MOCK: Every claim in a generated draft must be traceable to "
    "research findings or knowledge content already on file for the contact; "
    "none of the text in this document represents a real prospect, real deal "
    "terms, or real financial figures."
)


class SeedEnvironmentError(RuntimeError):
    """Raised when the seed is invoked outside an allowed local/mock environment."""


class SeedPreconditionError(RuntimeError):
    """Raised when a required precondition (e.g. the tenant row) is missing."""


@dataclass(frozen=True)
class SeedResult:
    created: bool
    document_id: uuid.UUID | None
    chunk_count: int
    skipped_reason: str | None = None


def ensure_seed_env_allowed(settings: Settings) -> None:
    if settings.app_env not in _ALLOWED_SEED_ENVS:
        raise SeedEnvironmentError(
            f"Refusing to seed local grounding data: APP_ENV={settings.app_env!r} is not one "
            f"of {sorted(_ALLOWED_SEED_ENVS)}. This seed is local/mock/demo-only."
        )


def build_seed_principal(tenant_id: uuid.UUID) -> CurrentPrincipal:
    """Owner principal mirroring app/auth/local_mock.py's local mock identity."""
    return CurrentPrincipal(
        provider_user_id=_LOCAL_MOCK_PROVIDER_USER_ID,
        provider_session_ref=_LOCAL_MOCK_PROVIDER_SESSION_REF,
        user_id=_LOCAL_MOCK_USER_ID,
        email=_LOCAL_MOCK_EMAIL,
        tenant_id=tenant_id,
        role="owner",
        membership_version=1,
        mfa_verified=True,
    )


class _ContactStoreAdapter:
    """Local copy of the adapter used by routers/drafts.py — no request-time reuse."""

    def __init__(self, repo: ContactReadRepository) -> None:
        self._repo = repo

    async def get_contact(self, *, tenant_id: uuid.UUID, contact_id: uuid.UUID) -> Any | None:
        return await self._repo.get_contact_by_id(tenant_id=tenant_id, contact_id=contact_id)


async def seed_grounding_document(
    *,
    knowledge_repo: KnowledgeRepository,
    grounding_service: RAGGroundingService,
    principal: CurrentPrincipal,
    now: datetime,
) -> SeedResult:
    """Idempotently ingest the seed document through the gated add_document path."""
    existing = await knowledge_repo.get_document_by_title(
        tenant_id=principal.tenant_id, title=SEED_DOC_TITLE
    )
    if existing is not None:
        return SeedResult(
            created=False,
            document_id=existing.id,
            chunk_count=0,
            skipped_reason="already_seeded",
        )

    doc = await grounding_service.add_document(
        principal=principal,
        title=SEED_DOC_TITLE,
        content=SEED_DOC_CONTENT,
        source_url=None,
        now=now,
    )
    chunks = await knowledge_repo.list_chunks_for_grounding(tenant_id=principal.tenant_id)
    chunk_count = sum(1 for c in chunks if c.document_id == doc.id)
    return SeedResult(created=True, document_id=doc.id, chunk_count=chunk_count)


async def run(tenant_id: uuid.UUID = DEFAULT_TENANT_ID) -> SeedResult:
    ensure_seed_env_allowed(get_settings())
    principal = build_seed_principal(tenant_id)
    now = datetime.now(UTC)

    async with tenant_session(tenant_id=tenant_id, actor_id=_LOCAL_MOCK_USER_ID) as conn:
        audit = AuditService(AuditRepository(conn))
        billing = BillingGateService(BillingRepository(conn))
        rbac = RBACService()
        object_authz = ObjectAuthorizationService()
        knowledge_repo = KnowledgeRepository(conn)
        compliance = ComplianceGateService(ComplianceRepository(conn), audit.record)
        grounding_service = RAGGroundingService(
            knowledge_store=knowledge_repo,
            campaign_store=CampaignRepository(conn),
            contact_store=_ContactStoreAdapter(ContactReadRepository(conn)),
            rbac=rbac,
            object_authz=object_authz,
            billing=billing,
            compliance=compliance,
            audit_record=audit.record,
        )
        try:
            return await seed_grounding_document(
                knowledge_repo=knowledge_repo,
                grounding_service=grounding_service,
                principal=principal,
                now=now,
            )
        except IntegrityError as exc:
            raise SeedPreconditionError(
                f"Seeding failed for tenant {tenant_id}: the tenant/user rows this seed depends "
                "on do not exist in this database. Run the local demo tenant bootstrap "
                "(docs/evidence/phase-3-2-live-db-smoke.md) before seeding grounding data."
            ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tenant-id",
        type=uuid.UUID,
        default=DEFAULT_TENANT_ID,
        help="Target tenant UUID (default: local demo tenant).",
    )
    args = parser.parse_args(argv)

    try:
        result = asyncio.run(run(tenant_id=args.tenant_id))
    except SeedEnvironmentError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    except SeedPreconditionError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1

    if result.created:
        print(
            f"SEEDED: document_id={result.document_id} chunk_count={result.chunk_count} "
            f"tenant_id={args.tenant_id}"
        )
    else:
        print(
            f"SKIPPED ({result.skipped_reason}): document_id={result.document_id} "
            f"tenant_id={args.tenant_id}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
