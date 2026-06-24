"""Shared cursor-pagination request params and response envelope.

Used by list endpoints across product routers. Cursor pagination follows
docs/API_CONTRACT.md §8 (default page size 25, max 100). The cursor is an opaque
string whose encoding is owned by each resource's repository. ``limit`` is
clamped into ``[1, 100]`` rather than rejected, so callers cannot trip a 422 by
over-requesting.

P2-1 ships this as the shared foundation for later list routes; the import
endpoint itself does not paginate.
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator

DEFAULT_PAGE_LIMIT = 25
MAX_PAGE_LIMIT = 100
MIN_PAGE_LIMIT = 1


class PageParams(BaseModel):
    """Validated list query params. ``limit`` is clamped to ``[1, 100]``."""

    cursor: str | None = None
    limit: int = DEFAULT_PAGE_LIMIT

    @field_validator("limit")
    @classmethod
    def _clamp_limit(cls, value: int) -> int:
        return max(MIN_PAGE_LIMIT, min(MAX_PAGE_LIMIT, value))


class PageInfo(BaseModel):
    """Pagination metadata returned alongside a page of items."""

    next_cursor: str | None = None
    limit: int = DEFAULT_PAGE_LIMIT


class Page[ItemT](BaseModel):
    """Standard list envelope: ``{"items": [...], "page": {next_cursor, limit}}``."""

    items: list[ItemT]
    page: PageInfo
