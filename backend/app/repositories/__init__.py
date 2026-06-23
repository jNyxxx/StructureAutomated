"""Repositories: tenant-scoped SQL only, executed via the tenant DB helper."""

from app.repositories.research_repo import ResearchRepository

__all__ = ["ResearchRepository"]
