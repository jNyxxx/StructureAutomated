# Backend (`backend/`)

FastAPI + Python 3.12 backend for AutomatedStructure. Layered architecture
(`routers -> services -> repositories -> DB`); see
[../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) and the non-negotiable rules
in [../CLAUDE.md](../CLAUDE.md).

> **Phase 0, Slice 1 status:** scaffolding only. Package layout, tooling, and
> tests are in place; functional modules arrive in later slices.

## Local tooling

```bash
python -m venv .venv && . .venv/bin/activate    # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"

ruff check .            # lint
black --check .         # format check
mypy app                # type check
pytest                  # tests
```

## Layout

```text
app/
  main.py · config.py · database.py            # entrypoint / config / DB layer (placeholders)
  middleware/ routers/ schemas/ services/       # HTTP + business layers
  repositories/ models/                         # data layer (tenant-scoped SQL only)
  workers/ agents/ tools/                        # async jobs / LangGraph / agent tools
  integrations/ audit/ observability/           # adapters+secrets / audit / logging+boot guard
tests/                                          # pytest suite
```
