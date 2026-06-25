import { describe, expect, it } from "vitest";

import { ApiError } from "../api-client";
import {
  fetchBillingAccess,
  fetchBillingSubscription,
  fetchUsage,
  fetchTenantSettings,
  fetchMemberships,
  fetchAuditEvents,
  fetchComplianceProfile,
  fetchSuppressions,
  fetchContacts,
  fetchProspects,
  fetchContact,
  fetchCampaigns,
  fetchCampaign,
  fetchDraft,
  fetchDraftEvidence,
  fetchReviewItems,
  fetchReviewItem,
  fetchDeliverability,
  fetchDeliverabilityMailboxes,
  fetchOutcomes,
  fetchOutcomesRoi,
  importContacts,
  createCampaign,
  updateCampaign,
  selectCampaignContact,
  generateDraft,
  approveReviewItem,
  rejectReviewItem,
  requestReviewRegeneration,
  runSendGateDryRun,
  createSendIntent,
  createFollowUpRule,
  createFollowUpSchedule,
  mockRunFollowUpSchedule,
  createSuppression,
  reinstateSuppression,
  updateTenantSettings,
  updateComplianceProfile,
  createMockOutcomeEvent,
  mapBackendErrorToStatus,
  mapHealthResponseToStatus,
  parseAuthMeResponse,
} from "../backend-api";

/** Build a fetch stub exposing only what the client uses. */
function mockFetch(status: number, body: unknown, headers: Record<string, string> = {}): typeof fetch {
  const fake = {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(headers),
    text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
  };
  return (async () => fake as unknown as Response) as unknown as typeof fetch;
}

function authOptions(fetchImpl: typeof fetch) {
  return {
    fetchImpl,
    getToken: async () => "token-sentinel",
    getTenantId: () => "22222222-2222-2222-2222-222222222222",
  };
}

describe("backend status mapping", () => {
  it("maps ready success without claiming production readiness", () => {
    const status = mapHealthResponseToStatus({ status: "ready", request_id: "req_ready" }, "ready");

    expect(status.state).toBe("healthy");
    expect(status.label).toBe("Backend ready");
    expect(status.message).toContain("not production approval");
    expect(status.requestId).toBe("req_ready");
  });

  it("maps ready failures to unavailable/degraded-safe UI", () => {
    const status = mapBackendErrorToStatus(
      new ApiError("Request failed.", { code: "NETWORK_ERROR", status: 0, requestId: "req_down" }),
      "ready",
    );

    expect(status.state).toBe("unavailable");
    expect(status.label).toBe("Backend readiness unavailable");
    expect(status.requestId).toBe("req_down");
  });
});

describe("auth response parsing", () => {
  it("parses /auth/me principal response", () => {
    const parsed = parseAuthMeResponse({
      principal: {
        provider_user_id: "clerk_123",
        user_id: "11111111-1111-1111-1111-111111111111",
        email: "owner@example.com",
        tenant_id: "22222222-2222-2222-2222-222222222222",
        role: "tenant_owner",
        membership_version: 3,
        mfa_verified: true,
      },
    });

    expect(parsed.principal.tenant_id).toBe("22222222-2222-2222-2222-222222222222");
    expect(parsed.principal.role).toBe("tenant_owner");
  });
});

describe("billing/usage read fetchers (read-only)", () => {
  it("fetchBillingSubscription parses a mock subscription and preserves mock_only", async () => {
    const res = await fetchBillingSubscription(
      authOptions(
        mockFetch(200, {
          subscription: {
            plan: { key: "cre-demo", name: "CRE Outreach MVP Demo", features: { can_send: true }, mock_only: true },
            tenant_status: "active",
            grace_until: null,
            mock_only: true,
          },
        }),
      ),
    );

    expect(res.subscription.tenant_status).toBe("active");
    expect(res.subscription.mock_only).toBe(true);
  });

  it("fetchBillingAccess parses mock access gates and preserves mock_only", async () => {
    const res = await fetchBillingAccess(
      authOptions(
        mockFetch(200, {
          access: {
            is_active: true,
            can_send: true,
            can_run_agents: true,
            can_create_campaign: true,
            can_export: true,
            mock_only: true,
          },
        }),
      ),
    );

    expect(res.access.can_send).toBe(true);
    expect(res.access.mock_only).toBe(true);
  });

  it("fetchUsage parses a mock usage snapshot and preserves mock_only", async () => {
    const res = await fetchUsage(
      authOptions(
        mockFetch(200, {
          usage: {
            contacts_total: 69,
            contact_imports_total: 3,
            campaigns_total: 2,
            drafts_total: 15,
            outbound_mock_sent: 5,
            outbound_blocked: 0,
            send_gate_denied: 0,
            followups_mock_sent: 0,
            followups_skipped: 0,
            research_runs_total: 10,
            outcome_events_total: 0,
            mock_only: true,
          },
        }),
      ),
    );

    expect(res.usage.contacts_total).toBe(69);
    expect(res.usage.mock_only).toBe(true);
  });

  it("maps a backend error envelope to a typed ApiError without leaking the body", async () => {
    let caught: unknown;
    try {
      await fetchUsage(
        authOptions(
          mockFetch(403, {
            error: {
              code: "PERMISSION_DENIED",
              message: "You do not have access.",
              details: { field: "tenant_id" },
              request_id: "req_usage",
              correlation_id: "corr_usage",
            },
          }),
        ),
      );
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("PERMISSION_DENIED");
    expect(err.status).toBe(403);
    expect(err.requestId).toBe("req_usage");
  });

  it("maps a transport failure to NETWORK_ERROR with status 0", async () => {
    const failing = (async () => {
      throw new Error("socket secret sentinel");
    }) as unknown as typeof fetch;

    let caught: unknown;
    try {
      await fetchBillingSubscription(authOptions(failing));
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("NETWORK_ERROR");
    expect(err.status).toBe(0);
    expect(err.message).toBe("Request failed.");
  });
});

describe("settings/team/audit read fetchers (Phase 2)", () => {
  it("fetchTenantSettings parses current tenant settings and preserves mock_only", async () => {
    const res = await fetchTenantSettings(
      authOptions(
        mockFetch(200, {
          tenant: {
            id: "22222222-2222-2222-2222-222222222222",
            name: "Automated Structure",
            status: "active",
            settings: { timezone: "Asia/Manila", locale: "en-PH" },
            created_at: "2026-06-24T12:00:00Z",
            updated_at: "2026-06-24T12:00:00Z",
            mock_only: true,
          },
          mock_only: true,
        }),
      ),
    );

    expect(res.tenant.name).toBe("Automated Structure");
    expect(res.tenant.settings.timezone).toBe("Asia/Manila");
    expect(res.mock_only).toBe(true);
  });

  it("fetchMemberships parses current team memberships and preserves mock_only", async () => {
    const res = await fetchMemberships(
      authOptions(
        mockFetch(200, {
          memberships: [
            {
              id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
              user_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
              role: "owner",
              membership_version: 3,
              created_at: "2026-06-24T12:00:00Z",
              mock_only: true,
            },
          ],
          mock_only: true,
        }),
      ),
    );

    expect(res.memberships.length).toBe(1);
    expect(res.memberships[0].role).toBe("owner");
    expect(res.mock_only).toBe(true);
  });

  it("fetchAuditEvents parses audit events with pagination params and preserves mock_only", async () => {
    let lastUrl: string | undefined;
    const trackingFetch = async (input: RequestInfo | URL) => {
      lastUrl = String(input);
      return {
        ok: true,
        status: 200,
        headers: new Headers(),
        text: async () =>
          JSON.stringify({
            audit_events: [
              {
                id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
                event_type: "tenant.settings_updated",
                actor_user_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                object_type: "tenant",
                object_id: "22222222-2222-2222-2222-222222222222",
                request_id: "req_1",
                job_id: null,
                redacted_details: { changed_fields: ["name"], api_key: "[REDACTED]" },
                created_at: "2026-06-24T12:00:00Z",
              },
            ],
            page: {
              next_cursor: "cursor-123",
              limit: 25,
            },
            mock_only: true,
          }),
      } as Response;
    };

    const res = await fetchAuditEvents(
      authOptions(trackingFetch as unknown as typeof fetch),
      { cursor: "start", limit: 10 }
    );

    expect(lastUrl).toContain("cursor=start");
    expect(lastUrl).toContain("limit=10");
    expect(res.audit_events.length).toBe(1);
    expect(res.audit_events[0].event_type).toBe("tenant.settings_updated");
    expect(res.page.next_cursor).toBe("cursor-123");
    expect(res.mock_only).toBe(true);
  });
});

describe("contacts/prospects read fetchers (Phase 2)", () => {
  it("fetchContacts parses contact list responses with pagination", async () => {
    const res = await fetchContacts(
      authOptions(
        mockFetch(200, {
          contacts: [
            {
              id: "11111111-1111-1111-1111-111111111111",
              full_name: "Ava Santos",
              title: "Acquisitions Lead",
              email: "ava@example.com",
              domain: "example.com",
              company_name: "Northline Properties",
              created_at: "2026-06-24T12:00:00Z",
              updated_at: "2026-06-24T12:00:00Z",
            },
          ],
          page: { next_cursor: null, limit: 25 },
        }),
      ),
      { limit: 25 },
    );

    expect(res.contacts.length).toBe(1);
    expect(res.contacts[0].company_name).toBe("Northline Properties");
    expect(res.page.limit).toBe(25);
  });

  it("fetchProspects parses contact-backed prospect list responses", async () => {
    const res = await fetchProspects(
      authOptions(
        mockFetch(200, {
          prospects: [
            {
              id: "22222222-2222-2222-2222-222222222222",
              contact_id: "22222222-2222-2222-2222-222222222222",
              full_name: "Marco Reyes",
              title: "Managing Partner",
              email: "marco@example.com",
              domain: "example.com",
              company_name: "Harbor Asset Group",
              created_at: "2026-06-24T12:00:00Z",
              updated_at: "2026-06-24T12:00:00Z",
            },
          ],
          page: { next_cursor: "next", limit: 25 },
        }),
      ),
      { cursor: "start", limit: 25 },
    );

    expect(res.prospects.length).toBe(1);
    expect(res.prospects[0].contact_id).toBe("22222222-2222-2222-2222-222222222222");
    expect(res.page.next_cursor).toBe("next");
  });

  it("fetchContact parses contact detail responses", async () => {
    const res = await fetchContact(
      authOptions(
        mockFetch(200, {
          contact: {
            id: "33333333-3333-3333-3333-333333333333",
            full_name: "Nina Cruz",
            title: "Portfolio Director",
            email: "nina@example.com",
            domain: "example.com",
            company_name: "Civic Realty Partners",
            created_at: "2026-06-24T12:00:00Z",
            updated_at: "2026-06-24T12:00:00Z",
          },
        }),
      ),
      "33333333-3333-3333-3333-333333333333",
    );

    expect(res.contact.full_name).toBe("Nina Cruz");
    expect(res.contact.company_name).toBe("Civic Realty Partners");
  });

  it("maps a contacts backend error envelope to ApiError", async () => {
    let caught: unknown;
    try {
      await fetchContacts(
        authOptions(
          mockFetch(403, {
            error: {
              code: "PERMISSION_DENIED",
              message: "Contacts denied.",
              details: { scope: "read:contacts" },
              request_id: "req_contacts",
              correlation_id: "corr_contacts",
            },
          }),
        ),
      );
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("PERMISSION_DENIED");
    expect(err.status).toBe(403);
    expect(err.requestId).toBe("req_contacts");
  });

  it("maps a prospects transport failure to NETWORK_ERROR", async () => {
    const failing = (async () => {
      throw new Error("network down");
    }) as unknown as typeof fetch;

    let caught: unknown;
    try {
      await fetchProspects(authOptions(failing));
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("NETWORK_ERROR");
    expect(err.status).toBe(0);
  });
});

describe("campaigns read fetchers (Phase 2)", () => {
  it("fetchCampaigns parses campaign list responses with pagination", async () => {
    const res = await fetchCampaigns(
      authOptions(
        mockFetch(200, {
          campaigns: [
            {
              id: "44444444-4444-4444-4444-444444444444",
              created_by_user_id: "11111111-1111-1111-1111-111111111111",
              name: "CRE Multifamily Owner Outreach",
              description: "Backend mock campaign.",
              goal: "Book qualified owner calls.",
              target_segment: "CRE / Multifamily",
              notes: "Read-only mock data.",
              status: "review",
            },
          ],
          page: { next_cursor: null, limit: 25 },
        }),
      ),
      { limit: 25 },
    );

    expect(res.campaigns.length).toBe(1);
    expect(res.campaigns[0].name).toBe("CRE Multifamily Owner Outreach");
    expect(res.page.limit).toBe(25);
  });

  it("fetchCampaign parses campaign detail responses", async () => {
    const res = await fetchCampaign(
      authOptions(
        mockFetch(200, {
          campaign: {
            id: "55555555-5555-5555-5555-555555555555",
            created_by_user_id: null,
            name: "Industrial Investor Re-Engagement",
            description: null,
            goal: "Re-engage dormant investor prospects.",
            target_segment: "CRE / Industrial",
            notes: null,
            status: "draft",
          },
        }),
      ),
      "55555555-5555-5555-5555-555555555555",
    );

    expect(res.campaign.name).toBe("Industrial Investor Re-Engagement");
    expect(res.campaign.target_segment).toBe("CRE / Industrial");
  });

  it("maps a campaigns backend error envelope to ApiError", async () => {
    let caught: unknown;
    try {
      await fetchCampaigns(
        authOptions(
          mockFetch(403, {
            error: {
              code: "PERMISSION_DENIED",
              message: "Campaigns denied.",
              details: { scope: "read:campaigns" },
              request_id: "req_campaigns",
              correlation_id: "corr_campaigns",
            },
          }),
        ),
      );
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("PERMISSION_DENIED");
    expect(err.status).toBe(403);
    expect(err.requestId).toBe("req_campaigns");
  });

  it("maps a campaign detail transport failure to NETWORK_ERROR", async () => {
    const failing = (async () => {
      throw new Error("network down");
    }) as unknown as typeof fetch;

    let caught: unknown;
    try {
      await fetchCampaign(authOptions(failing), "55555555-5555-5555-5555-555555555555");
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("NETWORK_ERROR");
    expect(err.status).toBe(0);
  });
});

describe("draft detail/evidence read fetchers (Phase 2)", () => {
  it("fetchDraft parses draft detail responses", async () => {
    const res = await fetchDraft(
      authOptions(
        mockFetch(200, {
          draft: {
            id: "66666666-6666-6666-6666-666666666666",
            campaign_id: "44444444-4444-4444-4444-444444444444",
            contact_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
            status: "pending_review",
            subject: "Demo: reduce vacancy risk with grounded outreach",
            body: "Read-only backend mock draft body.",
            created_at: "2026-06-24T12:00:00Z",
            updated_at: "2026-06-24T12:00:00Z",
          },
          mock_only: true,
        }),
      ),
      "66666666-6666-6666-6666-666666666666",
    );

    expect(res.draft.subject).toContain("grounded outreach");
    expect(res.draft.status).toBe("pending_review");
    expect(res.mock_only).toBe(true);
  });

  it("fetchDraftEvidence parses evidence list responses with pagination", async () => {
    const res = await fetchDraftEvidence(
      authOptions(
        mockFetch(200, {
          evidence: [
            {
              id: "77777777-7777-7777-7777-777777777777",
              draft_id: "66666666-6666-6666-6666-666666666666",
              source_type: "knowledge_chunk",
              source_id: "88888888-8888-8888-8888-888888888888",
              content_snippet: "Approved backend mock evidence only.",
              created_at: "2026-06-24T12:00:00Z",
            },
          ],
          page: { next_cursor: null, limit: 25 },
          mock_only: true,
        }),
      ),
      "66666666-6666-6666-6666-666666666666",
      { limit: 25 },
    );

    expect(res.evidence.length).toBe(1);
    expect(res.evidence[0].content_snippet).toContain("backend mock evidence");
    expect(res.page.limit).toBe(25);
  });

  it("maps a draft backend error envelope to ApiError", async () => {
    let caught: unknown;
    try {
      await fetchDraft(
        authOptions(
          mockFetch(403, {
            error: {
              code: "PERMISSION_DENIED",
              message: "Draft denied.",
              details: { scope: "read:drafts" },
              request_id: "req_draft",
              correlation_id: "corr_draft",
            },
          }),
        ),
        "66666666-6666-6666-6666-666666666666",
      );
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("PERMISSION_DENIED");
    expect(err.status).toBe(403);
    expect(err.requestId).toBe("req_draft");
  });

  it("maps a draft evidence transport failure to NETWORK_ERROR", async () => {
    const failing = (async () => {
      throw new Error("network down");
    }) as unknown as typeof fetch;

    let caught: unknown;
    try {
      await fetchDraftEvidence(authOptions(failing), "66666666-6666-6666-6666-666666666666");
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("NETWORK_ERROR");
    expect(err.status).toBe(0);
  });
});

describe("review queue read fetchers (Phase 2)", () => {
  it("fetchReviewItems parses review item list responses with pagination", async () => {
    const res = await fetchReviewItems(
      authOptions(
        mockFetch(200, {
          review_items: [
            {
              id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
              draft_id: "66666666-6666-6666-6666-666666666666",
              campaign_id: "44444444-4444-4444-4444-444444444444",
              contact_id: "22222222-2222-2222-2222-222222222222",
              status: "pending_review",
              reviewer_user_id: null,
              action_reason: null,
              reviewed_at: null,
              created_at: "2026-06-24T12:00:00Z",
              updated_at: "2026-06-24T12:00:00Z",
            },
          ],
          page: { next_cursor: null, limit: 25 },
          mock_only: true,
        }),
      ),
      { limit: 25 },
    );

    expect(res.review_items.length).toBe(1);
    expect(res.review_items[0].status).toBe("pending_review");
    expect(res.page.limit).toBe(25);
  });

  it("fetchReviewItem parses review item detail responses", async () => {
    const res = await fetchReviewItem(
      authOptions(
        mockFetch(200, {
          review_item: {
            id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
            draft_id: "66666666-6666-6666-6666-666666666666",
            campaign_id: "44444444-4444-4444-4444-444444444444",
            contact_id: "22222222-2222-2222-2222-222222222222",
            status: "pending_review",
            reviewer_user_id: "11111111-1111-1111-1111-111111111111",
            action_reason: null,
            reviewed_at: null,
            created_at: "2026-06-24T12:00:00Z",
            updated_at: "2026-06-24T12:00:00Z",
          },
          mock_only: true,
        }),
      ),
      "cccccccc-cccc-cccc-cccc-cccccccccccc",
    );

    expect(res.review_item.id).toBe("cccccccc-cccc-cccc-cccc-cccccccccccc");
    expect(res.review_item.reviewer_user_id).toBe("11111111-1111-1111-1111-111111111111");
  });

  it("maps a review backend error envelope to ApiError", async () => {
    let caught: unknown;
    try {
      await fetchReviewItems(
        authOptions(
          mockFetch(403, {
            error: {
              code: "PERMISSION_DENIED",
              message: "Review denied.",
              details: { scope: "read:review" },
              request_id: "req_review",
              correlation_id: "corr_review",
            },
          }),
        ),
      );
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("PERMISSION_DENIED");
    expect(err.status).toBe(403);
    expect(err.requestId).toBe("req_review");
  });

  it("maps a review item transport failure to NETWORK_ERROR", async () => {
    const failing = (async () => {
      throw new Error("network down");
    }) as unknown as typeof fetch;

    let caught: unknown;
    try {
      await fetchReviewItem(authOptions(failing), "cccccccc-cccc-cccc-cccc-cccccccccccc");
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("NETWORK_ERROR");
    expect(err.status).toBe(0);
  });
});

describe("deliverability read fetchers (Phase 2)", () => {
  it("fetchDeliverability parses dashboard responses", async () => {
    const res = await fetchDeliverability(
      authOptions(
        mockFetch(200, {
          deliverability: {
            campaign_id: null,
            sent: 18,
            blocked: 11,
            duplicate_denied: 4,
            suppressed: 3,
            safety_denied: 4,
            throttled: 2,
            followup_sent: 0,
            followup_skipped: 5,
            mock_bounced: 1,
            mock_complained: 0,
            mock_opened: 7,
            mock_replied: 2,
            date_from: null,
            date_to: null,
            mock_only: true,
          },
          mock_only: true,
        }),
      ),
    );

    expect(res.deliverability.sent).toBe(18);
    expect(res.deliverability.suppressed).toBe(3);
    expect(res.mock_only).toBe(true);
  });

  it("fetchDeliverabilityMailboxes parses mailbox/domain health responses", async () => {
    const res = await fetchDeliverabilityMailboxes(
      authOptions(
        mockFetch(200, {
          mailbox_health: {
            mock_domain: "example.test",
            dkim_valid: true,
            spf_valid: true,
            dmarc_valid: false,
            reputation_score: 72,
            mock_only: true,
          },
          mock_only: true,
        }),
      ),
    );

    expect(res.mailbox_health.mock_domain).toBe("example.test");
    expect(res.mailbox_health.reputation_score).toBe(72);
  });

  it("maps a deliverability backend error envelope to ApiError", async () => {
    let caught: unknown;
    try {
      await fetchDeliverability(
        authOptions(
          mockFetch(403, {
            error: {
              code: "PERMISSION_DENIED",
              message: "Deliverability denied.",
              details: { scope: "read:deliverability" },
              request_id: "req_deliverability",
              correlation_id: "corr_deliverability",
            },
          }),
        ),
      );
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("PERMISSION_DENIED");
    expect(err.status).toBe(403);
    expect(err.requestId).toBe("req_deliverability");
  });

  it("maps a mailbox transport failure to NETWORK_ERROR", async () => {
    const failing = (async () => {
      throw new Error("network down");
    }) as unknown as typeof fetch;

    let caught: unknown;
    try {
      await fetchDeliverabilityMailboxes(authOptions(failing));
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("NETWORK_ERROR");
    expect(err.status).toBe(0);
  });
});

describe("outcomes/ROI read fetchers (Phase 2)", () => {
  it("fetchOutcomes parses outcomes dashboard responses", async () => {
    const res = await fetchOutcomes(
      authOptions(
        mockFetch(200, {
          outcomes: {
            campaign_id: null,
            reply_count: 5,
            positive_reply_count: 3,
            meeting_booked_count: 2,
            opportunity_count: 1,
            deal_won_count: 0,
            deal_lost_count: 0,
            unsubscribe_count: 1,
            bounce_count: 1,
            complaint_count: 0,
            reply_rate: 0.27,
            positive_reply_rate: 0.16,
            meeting_rate: 0.11,
            opportunity_rate: 0.05,
            win_rate: 0,
            date_from: null,
            date_to: null,
            mock_only: true,
          },
          mock_only: true,
        }),
      ),
    );

    expect(res.outcomes.reply_count).toBe(5);
    expect(res.outcomes.opportunity_count).toBe(1);
    expect(res.mock_only).toBe(true);
  });

  it("fetchOutcomesRoi parses ROI responses", async () => {
    const res = await fetchOutcomesRoi(
      authOptions(
        mockFetch(200, {
          roi: {
            campaign_id: "44444444-4444-4444-4444-444444444444",
            sent_count: 18,
            estimated_cost_cents: 48000,
            estimated_pipeline_value_cents: 4200000,
            estimated_won_value_cents: 0,
            estimated_roi_percent: 8650,
            mock_only: true,
          },
          mock_only: true,
        }),
      ),
      "44444444-4444-4444-4444-444444444444",
    );

    expect(res.roi.sent_count).toBe(18);
    expect(res.roi.estimated_pipeline_value_cents).toBe(4200000);
  });

  it("maps an outcomes backend error envelope to ApiError", async () => {
    let caught: unknown;
    try {
      await fetchOutcomes(
        authOptions(
          mockFetch(403, {
            error: {
              code: "PERMISSION_DENIED",
              message: "Outcomes denied.",
              details: { scope: "read:outcomes" },
              request_id: "req_outcomes",
              correlation_id: "corr_outcomes",
            },
          }),
        ),
      );
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("PERMISSION_DENIED");
    expect(err.status).toBe(403);
    expect(err.requestId).toBe("req_outcomes");
  });

  it("maps an ROI transport failure to NETWORK_ERROR", async () => {
    const failing = (async () => {
      throw new Error("network down");
    }) as unknown as typeof fetch;

    let caught: unknown;
    try {
      await fetchOutcomesRoi(authOptions(failing), "44444444-4444-4444-4444-444444444444");
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("NETWORK_ERROR");
    expect(err.status).toBe(0);
  });
});

describe("compliance/suppressions read fetchers (Phase 2)", () => {
  it("fetchComplianceProfile parses the backend mock compliance profile", async () => {
    const res = await fetchComplianceProfile(
      authOptions(
        mockFetch(200, {
          compliance_profile: {
            jurisdiction: "US",
            sending_review_required: true,
            live_sending_allowed: false,
            sms_allowed: false,
            mock_only: true,
          },
          mock_only: true,
        }),
      ),
    );

    expect(res.compliance_profile.jurisdiction).toBe("US");
    expect(res.compliance_profile.sending_review_required).toBe(true);
    expect(res.mock_only).toBe(true);
  });

  it("fetchSuppressions parses suppressions with pagination params and preserves mock_only", async () => {
    let lastUrl: string | undefined;
    const trackingFetch = async (input: RequestInfo | URL) => {
      lastUrl = String(input);
      return {
        ok: true,
        status: 200,
        headers: new Headers(),
        text: async () =>
          JSON.stringify({
            suppressions: [
              {
                id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
                channel: "email",
                reason: "manual block",
                source: "mock",
                never_contact: true,
                created_at: "2026-06-24T12:00:00Z",
                revoked_at: null,
                active: true,
                mock_only: true,
              },
            ],
            page: {
              next_cursor: null,
              limit: 25,
            },
            mock_only: true,
          }),
      } as Response;
    };

    const res = await fetchSuppressions(
      authOptions(trackingFetch as unknown as typeof fetch),
      { limit: 25 },
    );

    expect(lastUrl).toContain("limit=25");
    expect(res.suppressions.length).toBe(1);
    expect(res.suppressions[0].active).toBe(true);
    expect(res.mock_only).toBe(true);
  });

  it("maps a compliance backend error envelope to ApiError", async () => {
    let caught: unknown;
    try {
      await fetchComplianceProfile(
        authOptions(
          mockFetch(403, {
            error: {
              code: "PERMISSION_DENIED",
              message: "Compliance profile denied.",
              details: { scope: "read:compliance" },
              request_id: "req_compliance",
              correlation_id: "corr_compliance",
            },
          }),
        ),
      );
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("PERMISSION_DENIED");
    expect(err.status).toBe(403);
    expect(err.requestId).toBe("req_compliance");
  });

  it("maps a suppressions transport failure to NETWORK_ERROR", async () => {
    const failing = (async () => {
      throw new Error("network down");
    }) as unknown as typeof fetch;

    let caught: unknown;
    try {
      await fetchSuppressions(authOptions(failing));
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("NETWORK_ERROR");
    expect(err.status).toBe(0);
  });
});

const ids = {
  tenant: "22222222-2222-2222-2222-222222222222",
  user: "11111111-1111-1111-1111-111111111111",
  campaign: "44444444-4444-4444-4444-444444444444",
  contact: "22222222-2222-2222-2222-222222222222",
  draft: "66666666-6666-6666-6666-666666666666",
  review: "cccccccc-cccc-cccc-cccc-cccccccccccc",
  outbound: "99999999-9999-9999-9999-999999999999",
  followupRule: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  followupSchedule: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
  suppression: "dddddddd-dddd-dddd-dddd-dddddddddddd",
};

function trackingFetch(
  status: number,
  body: unknown,
  onRequest?: (input: RequestInfo | URL, init?: RequestInit) => void,
): typeof fetch {
  const fake = {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(),
    text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
  };
  return (async (input: RequestInfo | URL, init?: RequestInit) => {
    onRequest?.(input, init);
    return fake as unknown as Response;
  }) as unknown as typeof fetch;
}

describe("safe local/mock action wrappers (P2-Exit-2a)", () => {
  it("parses success responses for all new safe local/mock wrappers", async () => {
    const importRes = await importContacts(
      authOptions(
        mockFetch(200, {
          import: {
            id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            status: "completed",
            total_rows: 3,
            valid_rows: 2,
            invalid_rows: 1,
            duplicate_rows: 0,
          },
          idempotency_replay: false,
        }),
      ),
      { csv_text: "full_name,email\nAva Santos,ava@example.com", source_filename: "contacts.csv" },
    );
    expect(importRes.import?.valid_rows).toBe(2);

    const campaignBody = {
      campaign: {
        id: ids.campaign,
        created_by_user_id: ids.user,
        name: "CRE Owners",
        description: "Local mock campaign",
        goal: "Book calls",
        target_segment: "CRE",
        notes: "Safe mock only",
        status: "draft",
      },
      idempotency_replay: false,
      mock_only: true,
    };
    expect((await createCampaign(authOptions(mockFetch(200, campaignBody)), { name: "CRE Owners" })).campaign?.id).toBe(ids.campaign);
    expect((await updateCampaign(authOptions(mockFetch(200, campaignBody)), ids.campaign, { status: "review" })).campaign?.status).toBe("draft");

    const selection = await selectCampaignContact(
      authOptions(
        mockFetch(200, {
          campaign_contact: {
            id: "12121212-1212-1212-1212-121212121212",
            campaign_id: ids.campaign,
            contact_id: ids.contact,
            status: "selected",
          },
          idempotency_replay: false,
          mock_only: true,
        }),
      ),
      ids.campaign,
      { contact_id: ids.contact },
    );
    expect(selection.campaign_contact?.status).toBe("selected");

    const draftBody = {
      draft: {
        id: ids.draft,
        campaign_id: ids.campaign,
        contact_id: ids.contact,
        status: "pending_review",
        subject: "Mock grounded outreach",
        body: "Safe local mock draft.",
        created_at: "2026-06-24T12:00:00Z",
        updated_at: "2026-06-24T12:00:00Z",
      },
      idempotency_replay: false,
      mock_only: true,
    };
    expect((await generateDraft(authOptions(mockFetch(200, draftBody)), { campaign_id: ids.campaign, contact_id: ids.contact })).draft?.id).toBe(ids.draft);

    const reviewBody = {
      review_item: {
        id: ids.review,
        draft_id: ids.draft,
        campaign_id: ids.campaign,
        contact_id: ids.contact,
        status: "approved",
        reviewer_user_id: ids.user,
        action_reason: "Safe mock approval.",
        reviewed_at: "2026-06-24T12:00:00Z",
        created_at: "2026-06-24T12:00:00Z",
        updated_at: "2026-06-24T12:00:00Z",
      },
      idempotency_replay: false,
      mock_only: true,
    };
    expect((await approveReviewItem(authOptions(mockFetch(200, reviewBody)), ids.review, { reason: "ok" })).review_item?.status).toBe("approved");
    expect((await rejectReviewItem(authOptions(mockFetch(200, reviewBody)), ids.review, { reason: "no" })).review_item?.id).toBe(ids.review);
    expect((await requestReviewRegeneration(authOptions(mockFetch(200, reviewBody)), ids.review, { reason: "revise" })).review_item?.id).toBe(ids.review);

    const gate = await runSendGateDryRun(
      authOptions(
        mockFetch(200, {
          send_gate_result: {
            id: "13131313-1313-1313-1313-131313131313",
            draft_id: ids.draft,
            status: "allowed",
            deny_reason_code: null,
            created_at: "2026-06-24T12:00:00Z",
          },
          idempotency_replay: false,
          mock_only: true,
        }),
      ),
      { draft_id: ids.draft },
    );
    expect(gate.send_gate_result?.status).toBe("allowed");

    const sendIntent = await createSendIntent(
      authOptions(
        mockFetch(200, {
          result: {
            outbound_message_id: ids.outbound,
            status: "mock_sent",
            sent_at: "2026-06-24T12:00:00Z",
          },
          idempotency_replay: false,
          mock_only: true,
        }),
      ),
      { draft_id: ids.draft },
    );
    expect(sendIntent.result?.outbound_message_id).toBe(ids.outbound);

    const rule = await createFollowUpRule(
      authOptions(
        mockFetch(200, {
          followup_rule: {
            id: ids.followupRule,
            campaign_id: ids.campaign,
            delay_seconds: 86400,
            created_at: "2026-06-24T12:00:00Z",
            updated_at: "2026-06-24T12:00:00Z",
          },
          idempotency_replay: false,
          mock_only: true,
        }),
      ),
      { campaign_id: ids.campaign, delay_seconds: 86400 },
    );
    expect(rule.followup_rule?.delay_seconds).toBe(86400);

    const scheduleBody = {
      followup_schedule: {
        id: ids.followupSchedule,
        campaign_id: ids.campaign,
        contact_id: ids.contact,
        original_outbound_message_id: ids.outbound,
        original_draft_id: ids.draft,
        followup_rule_id: ids.followupRule,
        status: "scheduled",
        run_after: "2026-06-25T12:00:00Z",
        created_at: "2026-06-24T12:00:00Z",
        updated_at: "2026-06-24T12:00:00Z",
      },
      idempotency_replay: false,
      mock_only: true,
    };
    expect((await createFollowUpSchedule(authOptions(mockFetch(200, scheduleBody)), { original_outbound_message_id: ids.outbound })).followup_schedule?.id).toBe(ids.followupSchedule);
    expect((await mockRunFollowUpSchedule(authOptions(mockFetch(200, scheduleBody)), ids.followupSchedule)).followup_schedule?.status).toBe("scheduled");

    const suppressionBody = {
      suppression: {
        id: ids.suppression,
        channel: "email",
        reason: "manual block",
        source: "manual",
        never_contact: true,
        created_at: "2026-06-24T12:00:00Z",
        revoked_at: null,
        active: true,
      },
      idempotency_replay: false,
      mock_only: true,
    };
    expect((await createSuppression(authOptions(mockFetch(200, suppressionBody)), { contact_identifier: "blocked@example.com", reason: "manual block" })).suppression.id).toBe(ids.suppression);
    expect((await reinstateSuppression(authOptions(mockFetch(200, suppressionBody)), ids.suppression)).suppression.active).toBe(true);

    const tenantBody = {
      tenant: {
        id: ids.tenant,
        name: "Automated Structure Updated",
        status: "active",
        settings: { timezone: "Asia/Manila" },
        created_at: "2026-06-24T12:00:00Z",
        updated_at: "2026-06-24T12:00:00Z",
      },
      idempotency_replay: false,
      mock_only: true,
    };
    expect((await updateTenantSettings(authOptions(mockFetch(200, tenantBody)), { name: "Automated Structure Updated" })).tenant.name).toContain("Updated");

    const complianceBody = {
      compliance_profile: {
        jurisdiction: "US",
        sending_review_required: true,
        live_sending_allowed: false,
        sms_allowed: false,
      },
      idempotency_replay: false,
      mock_only: true,
    };
    expect((await updateComplianceProfile(authOptions(mockFetch(200, complianceBody)), { jurisdiction: "US" })).compliance_profile.live_sending_allowed).toBe(false);

    const outcome = await createMockOutcomeEvent(
      authOptions(
        mockFetch(200, {
          outcome_event: {
            id: "14141414-1414-1414-1414-141414141414",
            campaign_id: ids.campaign,
            contact_id: ids.contact,
            outbound_message_id: ids.outbound,
            event_type: "reply_positive",
            note: "Safe mock event.",
            occurred_at: "2026-06-24T12:00:00Z",
            created_at: "2026-06-24T12:00:00Z",
          },
          mock_only: true,
        }),
      ),
      { campaign_id: ids.campaign, contact_id: ids.contact, outbound_message_id: ids.outbound, event_type: "reply_positive" },
    );
    expect(outcome.outcome_event.event_type).toBe("reply_positive");
  });

  it("sends generated Idempotency-Key headers on unsafe writes", async () => {
    const seen = new Map<string, string | null>();
    const fetchImpl = trackingFetch(
      200,
      {
        campaign: {
          id: ids.campaign,
          created_by_user_id: ids.user,
          name: "CRE Owners",
          description: null,
          goal: null,
          target_segment: null,
          notes: null,
          status: "draft",
        },
        idempotency_replay: false,
      },
      (input, init) => {
        seen.set(String(input), new Headers(init?.headers).get("Idempotency-Key"));
      },
    );

    await createCampaign(authOptions(fetchImpl), { name: "CRE Owners" });

    const key = [...seen.values()][0];
    expect(key).toMatch(/^as-campaigns-create-/);
  });

  it("respects caller-provided Idempotency-Key", async () => {
    let header: string | null = null;
    const fetchImpl = trackingFetch(
      200,
      {
        campaign: {
          id: ids.campaign,
          created_by_user_id: ids.user,
          name: "CRE Owners",
          description: null,
          goal: null,
          target_segment: null,
          notes: null,
          status: "draft",
        },
        idempotency_replay: true,
      },
      (_input, init) => {
        header = new Headers(init?.headers).get("Idempotency-Key");
      },
    );

    await createCampaign({ ...authOptions(fetchImpl), idempotencyKey: "caller-key-123" }, { name: "CRE Owners" });

    expect(header).toBe("caller-key-123");
  });

  it("maps backend error envelopes from unsafe writes to ApiError", async () => {
    let caught: unknown;
    try {
      await createCampaign(
        authOptions(
          mockFetch(409, {
            error: {
              code: "IDEMPOTENCY_CONFLICT",
              message: "Idempotency-Key was reused with a different request.",
              details: { route: "campaigns" },
              request_id: "req_write",
              correlation_id: "corr_write",
            },
          }),
        ),
        { name: "CRE Owners" },
      );
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("IDEMPOTENCY_CONFLICT");
    expect(err.status).toBe(409);
    expect(err.requestId).toBe("req_write");
  });

  it("maps transport failures from unsafe writes to NETWORK_ERROR", async () => {
    const failing = (async () => {
      throw new Error("network down");
    }) as unknown as typeof fetch;

    let caught: unknown;
    try {
      await runSendGateDryRun(authOptions(failing), { draft_id: ids.draft });
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const err = caught as ApiError;
    expect(err.code).toBe("NETWORK_ERROR");
    expect(err.status).toBe(0);
  });
});
