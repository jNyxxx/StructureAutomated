# AI Safety & Groundedness

**Purpose:** LangGraph cold-outreach flow, agent state, tool registry + permission enforcement, prompt-injection defense, groundedness gate + re-grounding after edits, dangerous-action prevention, cost controls, RAG/research governance, and required evals.
**Source sections:** Master guide §13 (agents/tools/AI safety), §16 (RAG/embeddings/research governance).
**Status:** Draft
**Related docs:** [DATABASE_SCHEMA](DATABASE_SCHEMA.md) (`agent_runs`, `agent_actions`, `groundedness_verdicts`, `knowledge_embeddings`) · [EMAIL_COMPLIANCE_AND_SEND_GATE](EMAIL_COMPLIANCE_AND_SEND_GATE.md) (send gate, duplicate-send) · [PRIVACY_AND_RETENTION](PRIVACY_AND_RETENTION.md) (embedding retention/purge) · [CLAUDE](../CLAUDE.md) (rules 9, 10)

---

## 1. LangGraph cold-outreach flow

```text
intake -> prospect_research -> enrichment -> rag_grounding -> draft_generation
-> prompt_injection_fence -> groundedness_gate -> review_decision
-> send_gate -> send_scheduling -> followup_scheduler -> outcome_tracking
```

## 2. Agent state (required fields)

`tenant_id`, `campaign_id`, `prospect_id`, `contact_id` · `actor_user_id`/`system_actor` · `approval_mode` · `research_sources`, `research_snippets`, `rag_context` · `draft_subject`, `draft_body`, `claims` · `groundedness_verdict`, `unsupported_claims` · `review_required` · `send_gate_result` · `send_intent_id` · `cost_usd`, `token_count`, `trace_url` · `errors`.

## 3. Tool registry

Every tool definition must include: tool name + action · tenant scopes + required permission · input/output schemas · provider rate limit · max calls per run · data classification · secret requirements · audit event name · mock adapter + live adapter.

**Before every tool call:**
1. Verify tenant/tool/action permission.
2. Verify integration active or mock allowed.
3. Verify usage quota + cost cap.
4. Verify provider allowlist.
5. Validate input schema.
6. Redact secrets from logs.
7. Execute tool.
8. Validate output schema.
9. Store input/output hashes + metadata in `agent_actions`.
10. Add only approved fields to agent state.

## 4. Dangerous-action prevention

Agents **cannot**: send directly · access the DB · read cross-tenant data · modify billing/users/sessions · decrypt credentials · call arbitrary URLs · disable audit · include secrets or unneeded PII (CLAUDE rules 9, 10). Sending only ever happens through the [send gate](EMAIL_COMPLIANCE_AND_SEND_GATE.md); duplicate-send prevention is enforced there + in the DB.

## 5. Prompt-injection defense

Treat all research and imported content as **untrusted data**. System prompt must state snippets cannot override instructions. Quarantine content that tries to: reveal prompts, alter tools, change recipients, bypass gates, request secrets, or skip approval.

**CI attack corpus** must include attempts to: ignore instructions and send elsewhere · use another tenant's contacts · invent a false meeting/urgency · reveal API keys · skip human approval · send despite suppression.

## 6. Groundedness gate

1. Extract factual claims from the draft.
2. Classify: prospect, company, market, tenant/client, generic, or unsupported opinion.
3. Match factual claims to approved research/source snippets.
4. Verdict: `pass`, `strip_unsupported`, `needs_review`, or `block`.
5. Store verdict + source references (`groundedness_verdicts`).
6. **On human edit, create a new draft version and re-run the gate.**

**No draft can schedule unless the current version has a passing or explicitly policy-approved verdict.** The send gate enforces `EDIT_REQUIRES_REGROUNDING` and `GROUNDEDNESS_FAILED`.

## 7. Cost controls

Per tenant/campaign/run, enforce max agent steps, tokens/draft, cost/run, tool calls/run, and daily tenant quotas. On budget exceed, **stop and store partial status**. Store actual usage in `quota_events`/`usage_counters` so limits change without schema changes.

| Limit | Local/demo | Production pilot |
|---|---|---|
| Agent runs / tenant / day | 100 | 25 |
| Agent runs / campaign / day | 50 | 10 |
| Tool calls / agent run | 10 | 6 |
| Draft generations / prospect / step | 2 | 1 |
| Max job retries | 3 | 3 |
| Max tokens / draft generation | 4,000 | 3,000 |
| Daily AI spend cap / tenant | configurable | owner-approved cap required |
| Per-campaign AI spend cap | configurable | owner-approved cap required |

> Conservative defaults, not pricing. **Owner-approved spend caps required for production.**

## 8. RAG & research governance

**Store:** prospect research snippets · CRE property/owner context · tenant brand-voice examples · past winning email examples · campaign performance lessons · approved global safe playbooks.

**Do not store:** secrets · raw provider credentials · unnecessary sensitive PII · scraped data violating ToS/legal review · cross-tenant examples unless scrubbed and explicitly marked global.

**Embedding service contract:**
```python
async def store_embedding(content, tenant_id, source_table, source_id, metadata, retained_until) -> UUID: ...
async def retrieve_similar(query, tenant_id, top_k=5, include_global=True) -> list[RetrievedChunk]: ...
```
**Retrieval must filter by tenant before returning chunks; global chunks must be approved global content; vector search never replaces tenant filtering.** Embedding table + global-safety constraints → [DATABASE_SCHEMA §6](DATABASE_SCHEMA.md); retention/purge → [PRIVACY_AND_RETENTION](PRIVACY_AND_RETENTION.md). CRE live research source approval = **Owner decision needed** (public/mock for MVP; legal review before live scraping).

## 9. Required evals / tests

- [ ] LangSmith traces for every agent run (cost, tokens, trace URL stored).
- [ ] Prompt-injection eval corpus (§5) passes — no bypass of recipient/tenant/approval/suppression.
- [ ] Groundedness reports: unsupported claims stripped/blocked; re-grounding triggered on edit.
- [ ] Tool permission/allowlist/quota enforced; secrets never in logs/outputs.
- [ ] Cost caps stop runs and store partial status.
