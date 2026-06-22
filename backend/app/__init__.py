"""AutomatedStructure backend application package.

Layered architecture (see docs/ARCHITECTURE.md):
routers -> services -> repositories -> DB. Agents/tools never touch the DB and
never send. Workers reuse the same services/gates as routes.

This package is scaffolding only (Phase 0, Slice 1). Functional modules are
implemented in later slices.
"""
