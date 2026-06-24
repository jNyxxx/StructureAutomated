"""Shared cursor-pagination schema tests (Phase 2 P2-1 foundation)."""

from app.schemas.pagination import (
    DEFAULT_PAGE_LIMIT,
    MAX_PAGE_LIMIT,
    MIN_PAGE_LIMIT,
    Page,
    PageInfo,
    PageParams,
)


def test_page_params_default_limit() -> None:
    assert PageParams().limit == DEFAULT_PAGE_LIMIT


def test_page_params_clamps_above_max() -> None:
    assert PageParams(limit=10_000).limit == MAX_PAGE_LIMIT


def test_page_params_clamps_below_min() -> None:
    assert PageParams(limit=0).limit == MIN_PAGE_LIMIT


def test_page_envelope_serializes_items_and_cursor() -> None:
    page = Page[str](items=["a", "b"], page=PageInfo(next_cursor="cursor-2", limit=25))

    dumped = page.model_dump()

    assert dumped["items"] == ["a", "b"]
    assert dumped["page"]["next_cursor"] == "cursor-2"
    assert dumped["page"]["limit"] == 25
