# Docker local stack

Local development stack for AutomatedStructure. See `../docker-compose.yml`.

## Quick start

```bash
cp .env.example .env        # fill placeholders for local dev (never commit .env)
docker compose up           # db, backend, worker, frontend, n8n
```

Optional tiers:

```bash
docker compose --profile aws up     # + localstack (SQS, for queue work)
docker compose --profile cache up   # + redis (for the rate-limit store option)
```

## Services

| Service | Image / build | Port | Ready in |
|---|---|---|---|
| `db` | `pgvector/pgvector:pg16` | 5432 | now |
| `backend` | `./backend` (FastAPI) | 8000 | serves `/health` from Slice 3 |
| `worker` | `./backend` | — | loop in Slice 13 (placeholder until then) |
| `frontend` | `./frontend` (Next.js dev) | 3000 | pages in Slice 4 |
| `n8n` | `n8nio/n8n:1.70.0` | 5678 | now (orchestration glue only) |
| `localstack` | `localstack/localstack:3` (`--profile aws`) | 4566 | optional |
| `redis` | `redis:7-alpine` (`--profile cache`) | 6379 | optional |

## Postgres extensions

The `db` image **supports** `vector`, `citext`, `pgcrypto`, and `uuid-ossp`, but
they are **not** created at container init. They are installed by the Alembic
migration in Slice 5 so the production boot guard's migration-version check
remains the single source of truth. Do not add extension-creating init scripts
here.

## Notes

- Source is bind-mounted into `backend` and `frontend` for hot reload.
- `.env` is git-ignored; only `.env.example` (placeholders) is committed.
- n8n is orchestration/webhook glue only — never an authority for sends,
  billing, auth, or tenant access (see `../CLAUDE.md`).
