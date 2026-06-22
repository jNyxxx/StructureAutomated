"""Production-shaped adapter registry: select mock vs live by config.

Concrete provider integrations are NOT implemented here (later slices). This
provides the selection mechanism + the mocked-provider set used by the boot guard.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import StrEnum

from app.config import Settings


class ProviderKind(StrEnum):
    STRIPE = "stripe"
    MAILBOX = "mailbox"
    DNS = "dns"
    VERIFIER = "verifier"
    RESEARCH = "research"


def is_mock_enabled(settings: Settings, kind: ProviderKind) -> bool:
    return bool(getattr(settings, f"mock_{kind.value}"))


def mocked_kinds(settings: Settings) -> set[ProviderKind]:
    return {kind for kind in ProviderKind if is_mock_enabled(settings, kind)}


class ProviderAdapter(ABC):
    """Common base; mock and live adapters share one interface (CLAUDE.md rule 11)."""

    @property
    @abstractmethod
    def is_mock(self) -> bool: ...


_Factory = Callable[[], ProviderAdapter]


class AdapterRegistry:
    def __init__(self) -> None:
        self._factories: dict[ProviderKind, tuple[_Factory, _Factory]] = {}

    def register(self, kind: ProviderKind, mock_factory: _Factory, live_factory: _Factory) -> None:
        self._factories[kind] = (mock_factory, live_factory)

    def resolve(self, kind: ProviderKind, settings: Settings) -> ProviderAdapter:
        if kind not in self._factories:
            raise KeyError(f"no adapter registered for {kind.value}")
        mock_factory, live_factory = self._factories[kind]
        return mock_factory() if is_mock_enabled(settings, kind) else live_factory()


registry = AdapterRegistry()
