"""Slice 1 collection smoke test.

Confirms the test runner is wired and the application package imports as a
package. No application behaviour is asserted yet — functional tests arrive with
their slices (Slice 3 onward).
"""

import importlib


def test_app_package_imports() -> None:
    """The backend package and its layer sub-packages import cleanly."""
    app = importlib.import_module("app")
    assert app.__doc__ is not None

    for layer in (
        "middleware",
        "routers",
        "schemas",
        "services",
        "repositories",
        "models",
        "workers",
        "agents",
        "tools",
        "integrations",
        "audit",
        "observability",
    ):
        module = importlib.import_module(f"app.{layer}")
        assert module is not None
