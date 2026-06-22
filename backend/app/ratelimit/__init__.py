"""Rate-limit foundation: backend interface + counters.

The backend is a production-shaped interface; the in-memory adapter here is the
local/dev/test implementation (per API_CONTRACT §6, local may use in-memory/DB
as long as behavior matches). A shared-store adapter (Redis/Postgres) lands when
multi-process enforcement is required.
"""
