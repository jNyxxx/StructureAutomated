import type { ReactNode } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuditLogTable, formatSafeDetails } from "@/components/audit-log-table";
import { BillingBanner, readOnlyBillingStatus } from "@/components/billing-banner";
import { AuthGate, ClerkFrontendProvider, isLocalMockAuthAllowed, type FrontendAuthState } from "@/lib/clerk";
import { TenantProvider, TenantStatusCard } from "@/lib/tenant-context";

import AuditLogsPage from "../(app)/audit-logs/page";
import BillingPage from "../(app)/billing/page";
import AiDraftsPage from "../(app)/ai-drafts/page";
import CampaignsPage from "../(app)/campaigns/page";
import CampaignDetailPage from "../(app)/campaigns/[id]/page";
import CampaignDraftsPage from "../(app)/campaigns/[id]/drafts/page";
import NewCampaignPage from "../(app)/campaigns/new/page";
import DashboardPage from "../(app)/dashboard/page";
import DeliverabilityPage from "../(app)/deliverability/page";
import OutcomesPage from "../(app)/outcomes/page";
import PrivacyPage from "../(app)/privacy/page";
import ProspectsPage from "../(app)/prospects/page";
import ProspectImportPage from "../(app)/prospects/import/page";
import ReviewQueuePage from "../(app)/review-queue/page";
import SettingsPage from "../(app)/settings/page";
import ComplianceSettingsPage from "../(app)/settings/compliance/page";
import IntegrationsSettingsPage from "../(app)/settings/integrations/page";
import SecuritySettingsPage from "../(app)/settings/security/page";
import SuppressionSettingsPage from "../(app)/settings/suppression/page";
import TeamSettingsPage from "../(app)/settings/team/page";
import LoginPage from "../(auth)/login/page";

const signedInAuth: FrontendAuthState = {
  isLoaded: true,
  isSignedIn: true,
  userId: "11111111-1111-1111-1111-111111111111",
  email: "owner@example.com",
  mode: "local_mock",
  getToken: async () => "token-sentinel",
};

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ "x-request-id": "req_test" }),
    text: async () => JSON.stringify(body),
  } as Response;
}

const contactFixture = {
  id: "22222222-2222-2222-2222-222222222222",
  full_name: "Ava Santos",
  title: "Acquisitions Lead",
  email: null,
  domain: "northline.example",
  company_name: "Northline Properties",
  created_at: "2026-06-24T12:00:00Z",
  updated_at: "2026-06-24T12:00:00Z",
};

function renderWithTenant(node: ReactNode) {
  return render(
    <ClerkFrontendProvider value={signedInAuth}>
      <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
        {node}
      </TenantProvider>
    </ClerkFrontendProvider>,
  );
}

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.includes("/ready")) return jsonResponse({ status: "ready" });
      if (path.includes("/api/v1/tenants/current") && init?.method === "PATCH") {
        return jsonResponse({
          tenant: {
            id: "22222222-2222-2222-2222-222222222222",
            name: "Automated Structure Mock Tenant Updated",
            status: "active",
            settings: {
              timezone: "Asia/Manila",
              locale: "en-PH",
              mock_settings_update: true,
            },
            created_at: "2026-06-24T12:00:00Z",
            updated_at: "2026-06-24T12:30:00Z",
            mock_only: true,
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/tenants/current")) {
        return jsonResponse({
          tenant: {
            id: "22222222-2222-2222-2222-222222222222",
            name: "Automated Structure Test Tenant",
            status: "active",
            settings: {
              timezone: "UTC",
              locale: "en-US",
            },
            created_at: "2026-06-24T12:00:00Z",
            updated_at: "2026-06-24T12:00:00Z",
            mock_only: true,
          },
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/memberships")) {
        return jsonResponse({
          memberships: [
            {
              id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
              user_id: "11111111-1111-1111-1111-111111111111",
              role: "tenant_owner",
              membership_version: 1,
              created_at: "2026-06-24T12:00:00Z",
              mock_only: true,
            },
          ],
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/audit-events")) {
        return jsonResponse({
          audit_events: [
            {
              id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
              event_type: "send_gate.blocked",
              actor_user_id: "11111111-1111-1111-1111-111111111111",
              object_type: "mock_send",
              object_id: "22222222-2222-2222-2222-222222222222",
              request_id: "req_test_audit_001",
              job_id: null,
              redacted_details: {
                reason: "production_not_approved",
                contact_hash: "hash_demo_only",
                api_key: "[REDACTED]",
              },
              created_at: "2026-06-24T12:00:00Z",
            },
          ],
          page: {
            next_cursor: null,
            limit: 25,
          },
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/compliance/profile") && init?.method === "PUT") {
        return jsonResponse({
          compliance_profile: {
            jurisdiction: "US",
            sending_review_required: true,
            live_sending_allowed: false,
            sms_allowed: false,
            mock_only: true,
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/compliance/profile")) {
        return jsonResponse({
          compliance_profile: {
            jurisdiction: "US",
            sending_review_required: true,
            live_sending_allowed: false,
            sms_allowed: false,
            mock_only: true,
          },
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/suppressions/dddddddd-dddd-dddd-dddd-dddddddddddd/reinstate")) {
        return jsonResponse({
          suppression: {
            id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
            channel: "email",
            reason: "manual backend mock block reinstated",
            source: "mock_api",
            never_contact: false,
            created_at: "2026-06-24T12:00:00Z",
            revoked_at: "2026-06-24T12:30:00Z",
            active: false,
            mock_only: true,
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/suppressions") && init?.method === "POST") {
        return jsonResponse({
          suppression: {
            id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            channel: "email",
            reason: "Local/mock manual suppression from settings UI",
            source: "backend_mock_api",
            never_contact: true,
            created_at: "2026-06-24T12:30:00Z",
            revoked_at: null,
            active: true,
            mock_only: true,
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/suppressions")) {
        return jsonResponse({
          suppressions: [
            {
              id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
              channel: "email",
              reason: "manual backend mock block",
              source: "mock_api",
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
        });
      }
      if (path.includes("/api/v1/outcomes/roi")) {
        return jsonResponse({
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
        });
      }
      if (path.includes("/api/v1/outcomes")) {
        return jsonResponse({
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
        });
      }
      if (path.includes("/api/v1/deliverability/mailboxes")) {
        return jsonResponse({
          mailbox_health: {
            mock_domain: "example.test",
            dkim_valid: true,
            spf_valid: true,
            dmarc_valid: false,
            reputation_score: 72,
            mock_only: true,
          },
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/deliverability")) {
        return jsonResponse({
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
        });
      }
      if (path.includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc/approve")) {
        return jsonResponse({
          review_item: {
            id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
            draft_id: "66666666-6666-6666-6666-666666666666",
            campaign_id: "44444444-4444-4444-4444-444444444444",
            contact_id: "22222222-2222-2222-2222-222222222222",
            status: "approved",
            reviewer_user_id: "11111111-1111-1111-1111-111111111111",
            action_reason: "Approved by backend mock API.",
            reviewed_at: "2026-06-24T12:30:00Z",
            created_at: "2026-06-24T12:00:00Z",
            updated_at: "2026-06-24T12:30:00Z",
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc/reject")) {
        return jsonResponse({
          review_item: {
            id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
            draft_id: "66666666-6666-6666-6666-666666666666",
            campaign_id: "44444444-4444-4444-4444-444444444444",
            contact_id: "22222222-2222-2222-2222-222222222222",
            status: "rejected",
            reviewer_user_id: "11111111-1111-1111-1111-111111111111",
            action_reason: "Rejected by backend mock API.",
            reviewed_at: "2026-06-24T12:30:00Z",
            created_at: "2026-06-24T12:00:00Z",
            updated_at: "2026-06-24T12:30:00Z",
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc/request-regeneration")) {
        return jsonResponse({
          review_item: {
            id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
            draft_id: "66666666-6666-6666-6666-666666666666",
            campaign_id: "44444444-4444-4444-4444-444444444444",
            contact_id: "22222222-2222-2222-2222-222222222222",
            status: "needs_regeneration",
            reviewer_user_id: "11111111-1111-1111-1111-111111111111",
            action_reason: "Regeneration requested by backend mock API.",
            reviewed_at: "2026-06-24T12:30:00Z",
            created_at: "2026-06-24T12:00:00Z",
            updated_at: "2026-06-24T12:30:00Z",
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/send-gate/dry-run")) {
        return jsonResponse({
          send_gate_result: {
            id: "78787878-7878-7878-7878-787878787878",
            draft_id: "66666666-6666-6666-6666-666666666666",
            status: "allowed",
            deny_reason_code: null,
            created_at: "2026-06-24T12:35:00Z",
            mock_only: true,
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/send-intents")) {
        return jsonResponse({
          result: {
            outbound_message_id: "89898989-8989-8989-8989-898989898989",
            status: "mock_queued",
            sent_at: null,
            mock_only: true,
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/followups/schedules/a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1/mock-run")) {
        return jsonResponse({
          followup_schedule: {
            id: "a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1",
            campaign_id: "44444444-4444-4444-4444-444444444444",
            contact_id: "22222222-2222-2222-2222-222222222222",
            original_outbound_message_id: "89898989-8989-8989-8989-898989898989",
            original_draft_id: "66666666-6666-6666-6666-666666666666",
            followup_rule_id: "90909090-9090-9090-9090-909090909090",
            status: "mock_run_complete",
            run_after: "2026-06-25T12:35:00Z",
            created_at: "2026-06-24T12:36:00Z",
            updated_at: "2026-06-24T12:38:00Z",
            mock_only: true,
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/followups/rules")) {
        return jsonResponse({
          followup_rule: {
            id: "90909090-9090-9090-9090-909090909090",
            campaign_id: "44444444-4444-4444-4444-444444444444",
            delay_seconds: 86400,
            created_at: "2026-06-24T12:36:00Z",
            updated_at: "2026-06-24T12:36:00Z",
            mock_only: true,
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/followups/schedules")) {
        return jsonResponse({
          followup_schedule: {
            id: "a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1",
            campaign_id: "44444444-4444-4444-4444-444444444444",
            contact_id: "22222222-2222-2222-2222-222222222222",
            original_outbound_message_id: "89898989-8989-8989-8989-898989898989",
            original_draft_id: "66666666-6666-6666-6666-666666666666",
            followup_rule_id: "90909090-9090-9090-9090-909090909090",
            status: "scheduled",
            run_after: "2026-06-25T12:35:00Z",
            created_at: "2026-06-24T12:37:00Z",
            updated_at: "2026-06-24T12:37:00Z",
            mock_only: true,
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc")) {
        return jsonResponse({
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
        });
      }
      if (path.includes("/api/v1/review/items")) {
        return jsonResponse({
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
        });
      }
      if (path.includes("/api/v1/drafts/generate") && init?.method === "POST") {
        return jsonResponse({
          draft: {
            id: "12121212-1212-1212-1212-121212121212",
            campaign_id: "44444444-4444-4444-4444-444444444444",
            contact_id: "22222222-2222-2222-2222-222222222222",
            status: "pending_review",
            subject: "Generated backend mock draft",
            body: "Generated by backend mock API only. No live AI provider was called.",
            created_at: "2026-06-24T12:00:00Z",
            updated_at: "2026-06-24T12:00:00Z",
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/drafts/12121212-1212-1212-1212-121212121212/evidence")) {
        return jsonResponse({
          evidence: [
            {
              id: "34343434-3434-3434-3434-343434343434",
              draft_id: "12121212-1212-1212-1212-121212121212",
              source_type: "knowledge_chunk",
              source_id: "56565656-5656-5656-5656-565656565656",
              content_snippet: "Generated draft evidence reloaded from backend mock API.",
              created_at: "2026-06-24T12:00:00Z",
            },
          ],
          page: { next_cursor: null, limit: 25 },
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/drafts/12121212-1212-1212-1212-121212121212")) {
        return jsonResponse({
          draft: {
            id: "12121212-1212-1212-1212-121212121212",
            campaign_id: "44444444-4444-4444-4444-444444444444",
            contact_id: "22222222-2222-2222-2222-222222222222",
            status: "pending_review",
            subject: "Generated backend mock draft",
            body: "Generated by backend mock API only. No live AI provider was called.",
            created_at: "2026-06-24T12:00:00Z",
            updated_at: "2026-06-24T12:00:00Z",
          },
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/drafts/66666666-6666-6666-6666-666666666666/evidence")) {
        return jsonResponse({
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
        });
      }
      if (path.includes("/api/v1/drafts/66666666-6666-6666-6666-666666666666")) {
        return jsonResponse({
          draft: {
            id: "66666666-6666-6666-6666-666666666666",
            campaign_id: "44444444-4444-4444-4444-444444444444",
            contact_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
            status: "pending_review",
            subject: "Demo: backend mock grounded outreach",
            body: "Read-only backend mock draft body. This cannot be generated, approved, or sent.",
            created_at: "2026-06-24T12:00:00Z",
            updated_at: "2026-06-24T12:00:00Z",
          },
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/campaigns/") && path.includes("/contacts")) {
        return jsonResponse({
          campaign_contact: {
            id: "abababab-abab-abab-abab-abababababab",
            campaign_id: "44444444-4444-4444-4444-444444444444",
            contact_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
            status: "selected",
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/campaigns/") && init?.method === "PATCH") {
        return jsonResponse({
          campaign: {
            id: "44444444-4444-4444-4444-444444444444",
            created_by_user_id: "11111111-1111-1111-1111-111111111111",
            name: "CRE Multifamily Owner Outreach",
            description: "Backend mock campaign detail.",
            goal: "Book qualified owner calls.",
            target_segment: "CRE / Multifamily",
            notes: "Updated by backend mock API.",
            status: "review",
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/campaigns/") && init?.method !== "POST") {
        return jsonResponse({
          campaign: {
            id: "44444444-4444-4444-4444-444444444444",
            created_by_user_id: "11111111-1111-1111-1111-111111111111",
            name: "CRE Multifamily Owner Outreach",
            description: "Backend mock campaign detail.",
            goal: "Book qualified owner calls.",
            target_segment: "CRE / Multifamily",
            notes: "Read-only local/mock campaign detail.",
            status: "review",
          },
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/campaigns") && init?.method === "POST") {
        return jsonResponse({
          campaign: {
            id: "99999999-9999-9999-9999-999999999999",
            created_by_user_id: "11111111-1111-1111-1111-111111111111",
            name: "CRE Local Mock Campaign",
            description: "Created by backend mock API.",
            goal: "Book qualified owner conversations.",
            target_segment: "CRE / Local Mock",
            notes: "Safe mock create.",
            status: "draft",
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/campaigns")) {
        return jsonResponse({
          campaigns: [
            {
              id: "44444444-4444-4444-4444-444444444444",
              created_by_user_id: "11111111-1111-1111-1111-111111111111",
              name: "CRE Multifamily Owner Outreach",
              description: "Backend mock campaign row.",
              goal: "Book qualified owner calls.",
              target_segment: "CRE / Multifamily",
              notes: "Read-only local/mock campaign list.",
              status: "review",
            },
          ],
          page: { next_cursor: null, limit: 25 },
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/imports/contacts")) {
        return jsonResponse({
          import: {
            id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            status: "completed",
            total_rows: 3,
            valid_rows: 2,
            invalid_rows: 1,
            duplicate_rows: 0,
          },
          idempotency_replay: false,
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/prospects")) {
        return jsonResponse({
          prospects: [
            {
              id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
              contact_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
              full_name: "Ava Santos",
              title: "Acquisitions Lead",
              email: "ava@northline.com",
              domain: "northline.com",
              company_name: "Northline Properties",
              created_at: "2026-06-24T12:00:00Z",
              updated_at: "2026-06-24T12:00:00Z",
              mock_only: true,
            },
          ],
          page: {
            next_cursor: null,
            limit: 25,
          },
          mock_only: true,
        });
      }
      if (path.includes("/api/v1/prospects")) {
        return jsonResponse({
          prospects: [{ ...contactFixture, contact_id: contactFixture.id }],
          page: { next_cursor: null, limit: 25 },
        });
      }
      if (path.includes("/api/v1/contacts/")) {
        return jsonResponse({ contact: contactFixture });
      }
      if (path.includes("/api/v1/contacts")) {
        return jsonResponse({
          contacts: [contactFixture],
          page: { next_cursor: null, limit: 25 },
        });
      }
      if (path.includes("/auth/me")) {
        return jsonResponse({
          principal: {
            provider_user_id: "clerk_123",
            user_id: "11111111-1111-1111-1111-111111111111",
            email: "owner@example.com",
            tenant_id: "22222222-2222-2222-2222-222222222222",
            role: "tenant_owner",
            membership_version: 1,
            mfa_verified: true,
          },
        });
      }
      if (path.includes("/api/v1/billing/access")) {
        return jsonResponse({
          access: {
            is_active: true,
            can_send: true,
            can_run_agents: true,
            can_create_campaign: true,
            can_export: true,
            mock_only: true,
          },
        });
      }
      if (path.includes("/api/v1/billing/subscription")) {
        return jsonResponse({
          subscription: {
            plan: {
              key: "cre-demo",
              name: "CRE Outreach MVP Demo",
              features: {
                can_send: true,
                can_run_agents: true,
                can_create_campaign: true,
                can_export: true,
              },
              mock_only: true,
            },
            tenant_status: "active",
            grace_until: null,
            mock_only: true,
          },
        });
      }
      if (path.includes("/api/v1/usage")) {
        return jsonResponse({
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
        });
      }
      return jsonResponse({ status: "ok" });
    }),
  );
});

afterEach(() => {
  delete process.env.NEXT_PUBLIC_STRICT_BACKEND_MODE;
  vi.unstubAllGlobals();
});

describe("route shells render", () => {
  it("renders the Clerk login shell heading without password inputs", () => {
    render(<LoginPage />);
    expect(screen.getByRole("heading", { name: /sign in/i })).toBeTruthy();
    expect(screen.queryByLabelText(/password/i)).toBeNull();
  });

  it("renders the dashboard shell heading", () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <DashboardPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );
    expect(screen.getByRole("heading", { name: /dashboard/i })).toBeTruthy();
  });

  it("renders the billing shell and access model", () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <BillingPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );
    expect(screen.getByRole("heading", { name: /billing/i })).toBeTruthy();
    expect(screen.getAllByText(/Real Stripe deferred/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Derived access gates/i)).toBeTruthy();
    expect(screen.getByText(/Local\/mock MVP only/i)).toBeTruthy();
  });

  it("renders the audit log DataTable demo safely", () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <AuditLogsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );
    expect(screen.getByRole("heading", { name: /audit logs/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /audit log table/i })).toBeTruthy();
    expect(screen.getByText(/send_gate.blocked/i)).toBeTruthy();
    expect(screen.getByText(/Redaction visible/i)).toBeTruthy();
  });

  it("renders the privacy operations shell", () => {
    render(<PrivacyPage />);
    expect(screen.getByRole("heading", { name: /privacy/i })).toBeTruthy();
    expect(screen.getAllByText(/soft delete/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Vector purge/i).length).toBeGreaterThan(0);
  });

  it("renders the prospects DataTable demo safely", async () => {
    renderWithTenant(<ProspectsPage />);
    expect(screen.getByRole("heading", { name: /^prospects$/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /prospects demo table/i })).toBeTruthy();
    expect(screen.getByText(/Local\/mock MVP only/i)).toBeTruthy();
    await waitFor(() => expect(screen.getAllByText(/backend mock API/i).length).toBeGreaterThan(0));
    expect(screen.getByText(/Northline Properties/i)).toBeTruthy();
  });

  it("renders prospects fixture fallback when the backend is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("backend unavailable"); }));
    renderWithTenant(<ProspectsPage />);

    await waitFor(() => expect(screen.getAllByText(/fixture fallback/i).length).toBeGreaterThan(0));
    expect(screen.getByText(/Northline Properties/i)).toBeTruthy();
    expect(screen.getByText(/enrichment, campaign, export, and delete actions remain locked/i)).toBeTruthy();
    expect(screen.getByText(/No real sending/i)).toBeTruthy();
  });

  it("strict backend mode shows prospects backend error instead of fixture rows", async () => {
    process.env["NEXT_PUBLIC_" + "STRICT_BACKEND_MODE"] = "true";
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("backend unavailable"); }));
    renderWithTenant(<ProspectsPage />);

    await waitFor(() => expect(screen.getByText(/Strict backend mode: prospects unavailable/i)).toBeTruthy());
    expect(screen.getByText(/NETWORK_ERROR/i)).toBeTruthy();
    expect(screen.getByText(/Local\/mock MVP only/i)).toBeTruthy();
    expect(screen.queryByText(/Northline Properties/i)).toBeNull();
    expect(screen.queryByRole("button", { name: /Export contact/i })).toBeNull();
  });

  it("renders the CSV import wizard with LocalMockNotice and locked unsafe actions", () => {
    renderWithTenant(<ProspectImportPage />);
    expect(screen.getByRole("heading", { name: /import prospects/i })).toBeTruthy();
    expect(screen.getByText(/Local\/mock MVP only/i)).toBeTruthy();
    expect(screen.getAllByText(/Upload CSV/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("table", { name: /csv import preview rows/i })).toBeTruthy();
    expect(screen.getAllByText(/Backend mock import/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /^Import prospects$/i }).hasAttribute("disabled")).toBe(false);
    expect(screen.getByRole("button", { name: /Save mapping/i }).hasAttribute("disabled")).toBe(true);
    expect(screen.getAllByText(/No live scraping/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/No real enrichment/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/No real sending/i).length).toBeGreaterThan(0);
  });

  it("submits CSV import through the backend mock API wrapper with idempotency", async () => {
    renderWithTenant(<ProspectImportPage />);

    fireEvent.click(screen.getByRole("button", { name: /^Import prospects$/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock import succeeded/i)).toBeTruthy());
    expect(screen.getByText(/Total rows:/)).toBeTruthy();
    expect(screen.getByText(/Valid rows:/)).toBeTruthy();
    expect(screen.getByText(/Invalid rows:/)).toBeTruthy();
    expect(screen.getByText(/Duplicates:/)).toBeTruthy();
    expect(screen.getByRole("link", { name: /View prospects from backend mock API/i })).toBeTruthy();

    const fetchMock = vi.mocked(fetch);
    const importCall = fetchMock.mock.calls.find(([input]) => String(input).includes("/api/v1/imports/contacts"));
    expect(importCall).toBeTruthy();
    expect(importCall?.[1]?.method).toBe("POST");
    expect(new Headers(importCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-imports-contacts-/);
  });

  it("shows typed backend import errors without claiming success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        if (path.includes("/api/v1/imports/contacts")) {
          return jsonResponse(
            {
              error: {
                code: "CSV_VALIDATION_FAILED",
                message: "Import failed validation.",
                details: { row_count: 3 },
                request_id: "req_import_failed",
                correlation_id: "corr_import_failed",
              },
            },
            400,
          );
        }
        if (path.includes("/auth/me")) {
          return jsonResponse({
            principal: {
              provider_user_id: "clerk_123",
              user_id: "11111111-1111-1111-1111-111111111111",
              email: "owner@example.com",
              tenant_id: "22222222-2222-2222-2222-222222222222",
              role: "tenant_owner",
              membership_version: 1,
              mfa_verified: true,
            },
          });
        }
        if (path.includes("/api/v1/billing/access")) {
          return jsonResponse({ access: { is_active: true, can_send: true, can_run_agents: true, can_create_campaign: true, can_export: true, mock_only: true } });
        }
        if (path.includes("/api/v1/billing/subscription")) {
          return jsonResponse({ subscription: { plan: null, tenant_status: "active", grace_until: null, mock_only: true } });
        }
        return jsonResponse({ status: "ok" });
      }),
    );

    renderWithTenant(<ProspectImportPage />);
    fireEvent.click(screen.getByRole("button", { name: /^Import prospects$/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock import failed safely/i)).toBeTruthy());
    expect(screen.getByText(/Import failed validation/i)).toBeTruthy();
    expect(screen.getByText(/CSV_VALIDATION_FAILED/i)).toBeTruthy();
    expect(screen.queryByText(/Backend mock import succeeded/i)).toBeNull();
  });

  it("shows NETWORK_ERROR import failure without claiming success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        if (path.includes("/api/v1/imports/contacts")) throw new Error("backend unavailable");
        if (path.includes("/auth/me")) {
          return jsonResponse({
            principal: {
              provider_user_id: "clerk_123",
              user_id: "11111111-1111-1111-1111-111111111111",
              email: "owner@example.com",
              tenant_id: "22222222-2222-2222-2222-222222222222",
              role: "tenant_owner",
              membership_version: 1,
              mfa_verified: true,
            },
          });
        }
        if (path.includes("/api/v1/billing/access")) {
          return jsonResponse({ access: { is_active: true, can_send: true, can_run_agents: true, can_create_campaign: true, can_export: true, mock_only: true } });
        }
        if (path.includes("/api/v1/billing/subscription")) {
          return jsonResponse({ subscription: { plan: null, tenant_status: "active", grace_until: null, mock_only: true } });
        }
        return jsonResponse({ status: "ok" });
      }),
    );

    renderWithTenant(<ProspectImportPage />);
    fireEvent.click(screen.getByRole("button", { name: /^Import prospects$/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock import failed safely/i)).toBeTruthy());
    expect(screen.getByText(/NETWORK_ERROR/i)).toBeTruthy();
    expect(screen.queryByText(/Backend mock import succeeded/i)).toBeNull();
  });

  it("renders the campaigns DataTable demo safely", async () => {
    renderWithTenant(<CampaignsPage />);
    expect(screen.getByRole("heading", { name: /^campaigns$/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /campaigns demo table/i })).toBeTruthy();
    expect(screen.getByText(/Local\/mock MVP only/i)).toBeTruthy();
    await waitFor(() => expect(screen.getAllByText(/backend mock API/i).length).toBeGreaterThan(0));
    expect(screen.getByText(/CRE Multifamily Owner Outreach/i)).toBeTruthy();
    expect(screen.getByText(/Campaign mock actions/i)).toBeTruthy();
  });

  it("renders campaigns fixture fallback when the backend is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("backend unavailable"); }));
    renderWithTenant(<CampaignsPage />);

    await waitFor(() => expect(screen.getAllByText(/fixture fallback/i).length).toBeGreaterThan(0));
    expect(screen.getByText(/CRE Multifamily Owner Outreach/i)).toBeTruthy();
    expect(screen.getByText(/research, drafts, sends, follow-up, export, scraping, and providers remain locked/i)).toBeTruthy();
    expect(screen.getByText(/No real sending/i)).toBeTruthy();
  });

  it("strict backend mode shows campaigns backend error instead of fixture rows", async () => {
    process.env["NEXT_PUBLIC_" + "STRICT_BACKEND_MODE"] = "true";
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("backend unavailable"); }));
    renderWithTenant(<CampaignsPage />);

    await waitFor(() => expect(screen.getByText(/Strict backend mode: campaigns unavailable/i)).toBeTruthy());
    expect(screen.getByText(/NETWORK_ERROR/i)).toBeTruthy();
    expect(screen.getByText(/Local\/mock MVP only/i)).toBeTruthy();
    expect(screen.queryByText(/CRE Multifamily Owner Outreach/i)).toBeNull();
    expect(screen.queryByRole("button", { name: /Mock send/i })).toBeNull();
  });

  it("renders a campaign detail shell with LocalMockNotice and GateReasonBadge", async () => {
    renderWithTenant(<CampaignDetailPage params={{ id: "44444444-4444-4444-4444-444444444444" }} />);
    await waitFor(() => expect(screen.getByRole("heading", { name: /CRE Multifamily Owner Outreach/i })).toBeTruthy());
    expect(screen.getByText(/Local\/mock MVP only/i)).toBeTruthy();
    expect(screen.getByText(/Campaign update mock/i)).toBeTruthy();
    expect(screen.getByText(/Contact selection mock/i)).toBeTruthy();
    expect(screen.getByText(/Pipeline stage progress/i)).toBeTruthy();
  });

  it("renders the local/mock campaign builder shell", () => {
    renderWithTenant(<NewCampaignPage />);
    expect(screen.getByRole("heading", { name: /new campaign/i })).toBeTruthy();
    expect(screen.getByText(/Campaign builder shell/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /^Create campaign$/i }).hasAttribute("disabled")).toBe(false);
    expect(screen.getByRole("button", { name: /Save draft/i }).hasAttribute("disabled")).toBe(true);
    expect(screen.getByRole("button", { name: /Start research locked/i }).hasAttribute("disabled")).toBe(true);
    expect(screen.getByRole("button", { name: /Generate drafts locked/i }).hasAttribute("disabled")).toBe(true);
  });

  it("creates a campaign through the backend mock API with idempotency", async () => {
    renderWithTenant(<NewCampaignPage />);
    fireEvent.click(screen.getByRole("button", { name: /^Create campaign$/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock campaign created/i)).toBeTruthy());
    expect(screen.getByText(/CRE Local Mock Campaign/i)).toBeTruthy();
    expect(screen.getByRole("link", { name: /Open created campaign detail/i })).toBeTruthy();

    const fetchMock = vi.mocked(fetch);
    const createCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/campaigns") && init?.method === "POST" && !String(input).includes("/contacts"));
    expect(createCall).toBeTruthy();
    expect(new Headers(createCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-campaigns-create-/);
  });

  it("updates a campaign through the backend mock API with idempotency", async () => {
    renderWithTenant(<CampaignDetailPage params={{ id: "44444444-4444-4444-4444-444444444444" }} />);
    await waitFor(() => expect(screen.getByRole("button", { name: /^Update campaign$/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /^Update campaign$/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock campaign update succeeded/i)).toBeTruthy());
    const fetchMock = vi.mocked(fetch);
    const updateCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/campaigns/44444444-4444-4444-4444-444444444444") && init?.method === "PATCH");
    expect(updateCall).toBeTruthy();
    expect(new Headers(updateCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-campaigns-update-/);
  });

  it("selects a campaign contact through the backend mock API with idempotency", async () => {
    renderWithTenant(<CampaignDetailPage params={{ id: "44444444-4444-4444-4444-444444444444" }} />);
    await waitFor(() => expect(screen.getByRole("button", { name: /Select contact: Ava Santos/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Select contact: Ava Santos/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock contact selection succeeded/i)).toBeTruthy());
    const fetchMock = vi.mocked(fetch);
    const selectCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/campaigns/44444444-4444-4444-4444-444444444444/contacts") && init?.method === "POST");
    expect(selectCall).toBeTruthy();
    expect(new Headers(selectCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-campaigns-contacts-/);
  });

  it("shows typed backend campaign create errors without claiming success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path.includes("/api/v1/campaigns") && init?.method === "POST") {
          return jsonResponse(
            {
              error: {
                code: "CAMPAIGN_CREATE_DENIED",
                message: "Campaign create denied.",
                details: { gate: "can_create_campaign" },
                request_id: "req_campaign_create",
                correlation_id: "corr_campaign_create",
              },
            },
            403,
          );
        }
        if (path.includes("/auth/me")) {
          return jsonResponse({
            principal: {
              provider_user_id: "clerk_123",
              user_id: "11111111-1111-1111-1111-111111111111",
              email: "owner@example.com",
              tenant_id: "22222222-2222-2222-2222-222222222222",
              role: "tenant_owner",
              membership_version: 1,
              mfa_verified: true,
            },
          });
        }
        if (path.includes("/api/v1/billing/access")) {
          return jsonResponse({ access: { is_active: true, can_send: true, can_run_agents: true, can_create_campaign: true, can_export: true, mock_only: true } });
        }
        if (path.includes("/api/v1/billing/subscription")) {
          return jsonResponse({ subscription: { plan: null, tenant_status: "active", grace_until: null, mock_only: true } });
        }
        return jsonResponse({ status: "ok" });
      }),
    );

    renderWithTenant(<NewCampaignPage />);
    fireEvent.click(screen.getByRole("button", { name: /^Create campaign$/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock campaign create failed safely/i)).toBeTruthy());
    expect(screen.getByText(/Campaign create denied/i)).toBeTruthy();
    expect(screen.getByText(/CAMPAIGN_CREATE_DENIED/i)).toBeTruthy();
    expect(screen.queryByText(/Backend mock campaign created/i)).toBeNull();
  });

  it("shows NETWORK_ERROR campaign update failure without claiming success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path.includes("/api/v1/campaigns/44444444-4444-4444-4444-444444444444") && init?.method === "PATCH") throw new Error("backend unavailable");
        if (path.includes("/api/v1/prospects")) {
          return jsonResponse({ prospects: [{ id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee", contact_id: "cccccccc-cccc-cccc-cccc-cccccccccccc", full_name: "Ava Santos", title: "Acquisitions Lead", email: "ava@northline.com", domain: "northline.com", company_name: "Northline Properties", created_at: "2026-06-24T12:00:00Z", updated_at: "2026-06-24T12:00:00Z", mock_only: true }], page: { next_cursor: null, limit: 25 }, mock_only: true });
        }
        if (path.includes("/api/v1/campaigns/")) {
          return jsonResponse({ campaign: { id: "44444444-4444-4444-4444-444444444444", created_by_user_id: "11111111-1111-1111-1111-111111111111", name: "CRE Multifamily Owner Outreach", description: "Backend mock campaign detail.", goal: "Book qualified owner calls.", target_segment: "CRE / Multifamily", notes: "Read-only local/mock campaign detail.", status: "review" }, mock_only: true });
        }
        if (path.includes("/auth/me")) {
          return jsonResponse({ principal: { provider_user_id: "clerk_123", user_id: "11111111-1111-1111-1111-111111111111", email: "owner@example.com", tenant_id: "22222222-2222-2222-2222-222222222222", role: "tenant_owner", membership_version: 1, mfa_verified: true } });
        }
        if (path.includes("/api/v1/billing/access")) {
          return jsonResponse({ access: { is_active: true, can_send: true, can_run_agents: true, can_create_campaign: true, can_export: true, mock_only: true } });
        }
        if (path.includes("/api/v1/billing/subscription")) {
          return jsonResponse({ subscription: { plan: null, tenant_status: "active", grace_until: null, mock_only: true } });
        }
        return jsonResponse({ status: "ok" });
      }),
    );

    renderWithTenant(<CampaignDetailPage params={{ id: "44444444-4444-4444-4444-444444444444" }} />);
    await waitFor(() => expect(screen.getByRole("button", { name: /^Update campaign$/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /^Update campaign$/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock campaign action failed safely/i)).toBeTruthy());
    expect(screen.getByText(/NETWORK_ERROR/i)).toBeTruthy();
    expect(screen.queryByText(/Backend mock campaign update succeeded/i)).toBeNull();
  });

  it("renders the AI drafts workbench shell with LocalMockNotice and GateReasonBadge", () => {
    renderWithTenant(<AiDraftsPage />);
    expect(screen.getByRole("heading", { name: /ai drafts/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /ai drafts demo table/i })).toBeTruthy();
    expect(screen.getByText(/Local\/mock MVP only/i)).toBeTruthy();
    expect(screen.getAllByText(/Draft generation mock/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /^Generate mock draft$/i }).hasAttribute("disabled")).toBe(false);
    expect(screen.getByRole("button", { name: /Regenerate locked/i }).hasAttribute("disabled")).toBe(true);
    expect(screen.getByRole("button", { name: /Approve locked/i }).hasAttribute("disabled")).toBe(true);
    expect(screen.getAllByRole("button", { name: /Send locked/i }).every((button) => button.hasAttribute("disabled"))).toBe(true);
    expect(screen.getByText(/Research\/RAG workbench/i)).toBeTruthy();
  });

  it("generates a draft through the backend mock API with idempotency and reloads detail/evidence", async () => {
    renderWithTenant(<AiDraftsPage />);
    fireEvent.click(screen.getByRole("button", { name: /^Generate mock draft$/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock draft generation succeeded/i)).toBeTruthy());
    expect(screen.getAllByText(/Generated backend mock draft/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Generated draft evidence reloaded from backend mock API/i)).toBeTruthy();
    expect(screen.getByText(/No live AI provider was called/i)).toBeTruthy();

    const fetchMock = vi.mocked(fetch);
    const generateCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/drafts/generate") && init?.method === "POST");
    expect(generateCall).toBeTruthy();
    expect(new Headers(generateCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-drafts-generate-/);
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/api/v1/drafts/12121212-1212-1212-1212-121212121212"))).toBe(true);
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/api/v1/drafts/12121212-1212-1212-1212-121212121212/evidence"))).toBe(true);
  });

  it("loads draft detail and evidence from backend mock API while review/send actions stay locked", async () => {
    renderWithTenant(<AiDraftsPage />);
    fireEvent.click(screen.getByRole("button", { name: /View details for row 66666666-6666-6666-6666-666666666666/i }));

    await waitFor(() => expect(screen.getByText(/Draft detail and evidence loaded from backend mock API/i)).toBeTruthy());
    expect(screen.getByText(/Read-only backend mock draft body/i)).toBeTruthy();
    expect(screen.getByText(/Approved backend mock evidence only/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Approve draft/i }).hasAttribute("disabled")).toBe(true);
    expect(screen.getAllByRole("button", { name: /Regenerate/i }).every((button) => button.hasAttribute("disabled"))).toBe(true);
    expect(screen.getByRole("button", { name: /Send locked/i }).hasAttribute("disabled")).toBe(true);
  });

  it("shows typed backend draft generation errors without claiming success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path.includes("/api/v1/drafts/generate") && init?.method === "POST") {
          return jsonResponse(
            {
              error: {
                code: "DRAFT_GENERATION_DENIED",
                message: "Draft generation denied.",
                details: { gate: "can_run_agents" },
                request_id: "req_draft_generate",
                correlation_id: "corr_draft_generate",
              },
            },
            403,
          );
        }
        if (path.includes("/auth/me")) {
          return jsonResponse({ principal: { provider_user_id: "clerk_123", user_id: "11111111-1111-1111-1111-111111111111", email: "owner@example.com", tenant_id: "22222222-2222-2222-2222-222222222222", role: "tenant_owner", membership_version: 1, mfa_verified: true } });
        }
        if (path.includes("/api/v1/billing/access")) {
          return jsonResponse({ access: { is_active: true, can_send: true, can_run_agents: true, can_create_campaign: true, can_export: true, mock_only: true } });
        }
        if (path.includes("/api/v1/billing/subscription")) {
          return jsonResponse({ subscription: { plan: null, tenant_status: "active", grace_until: null, mock_only: true } });
        }
        return jsonResponse({ status: "ok" });
      }),
    );

    renderWithTenant(<AiDraftsPage />);
    fireEvent.click(screen.getByRole("button", { name: /^Generate mock draft$/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock draft generation failed safely/i)).toBeTruthy());
    expect(screen.getByText(/Draft generation denied/i)).toBeTruthy();
    expect(screen.getByText(/DRAFT_GENERATION_DENIED/i)).toBeTruthy();
    expect(screen.queryByText(/Backend mock draft generation succeeded/i)).toBeNull();
  });

  it("shows NETWORK_ERROR draft generation failure without claiming success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path.includes("/api/v1/drafts/generate") && init?.method === "POST") throw new Error("backend unavailable");
        if (path.includes("/auth/me")) {
          return jsonResponse({ principal: { provider_user_id: "clerk_123", user_id: "11111111-1111-1111-1111-111111111111", email: "owner@example.com", tenant_id: "22222222-2222-2222-2222-222222222222", role: "tenant_owner", membership_version: 1, mfa_verified: true } });
        }
        if (path.includes("/api/v1/billing/access")) {
          return jsonResponse({ access: { is_active: true, can_send: true, can_run_agents: true, can_create_campaign: true, can_export: true, mock_only: true } });
        }
        if (path.includes("/api/v1/billing/subscription")) {
          return jsonResponse({ subscription: { plan: null, tenant_status: "active", grace_until: null, mock_only: true } });
        }
        return jsonResponse({ status: "ok" });
      }),
    );

    renderWithTenant(<AiDraftsPage />);
    fireEvent.click(screen.getByRole("button", { name: /^Generate mock draft$/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock draft generation failed safely/i)).toBeTruthy());
    expect(screen.getByText(/NETWORK_ERROR/i)).toBeTruthy();
    expect(screen.queryByText(/Backend mock draft generation succeeded/i)).toBeNull();
  });

  it("renders draft fixture fallback when backend is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("backend unavailable"); }));
    renderWithTenant(<AiDraftsPage />);
    fireEvent.click(screen.getByRole("button", { name: /View details for row 66666666-6666-6666-6666-666666666666/i }));

    await waitFor(() => expect(screen.getByText(/fixture fallback/i)).toBeTruthy());
    expect(screen.getByText(/Hi team — based on public portfolio signals/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Approve draft/i }).hasAttribute("disabled")).toBe(true);
  });

  it("renders campaign-scoped draft shell", () => {
    renderWithTenant(<CampaignDraftsPage params={{ id: "cre-multifamily-demo" }} />);
    expect(screen.getByRole("heading", { name: /CRE Multifamily Owner Outreach drafts/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /ai drafts demo table/i })).toBeTruthy();
    expect(screen.getAllByText(/Draft generation mock/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /^Generate mock draft$/i })).toBeTruthy();
  });

  it("renders the review queue demo safely with LocalMockNotice and GateReasonBadge", async () => {
    renderWithTenant(<ReviewQueuePage />);
    expect(screen.getByRole("heading", { name: /review queue/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /review queue demo table/i })).toBeTruthy();
    expect(screen.getByText(/Local\/mock MVP only/i)).toBeTruthy();
    await waitFor(() => expect(screen.getAllByText(/backend mock API/i).length).toBeGreaterThan(0));
    expect(screen.getAllByText(/Review mock actions/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Review read refresh/i)).toBeTruthy();
    expect(screen.getByText(/Human approval never bypasses/i)).toBeTruthy();
  });

  it("loads review item detail from backend mock API while send/outbound actions stay locked", async () => {
    renderWithTenant(<ReviewQueuePage />);
    fireEvent.click(screen.getByRole("button", { name: /View details for row cccccccc-cccc-cccc-cccc-cccccccccccc/i }));

    await waitFor(() => expect(screen.getAllByText(/Review item loaded from backend mock API/i).length).toBeGreaterThan(0));
    expect(screen.getByRole("button", { name: /Approve review/i }).hasAttribute("disabled")).toBe(false);
    expect(screen.getByRole("button", { name: /Reject review/i }).hasAttribute("disabled")).toBe(false);
    expect(screen.getByRole("button", { name: /^Request regeneration$/i }).hasAttribute("disabled")).toBe(false);
    expect(screen.getByRole("button", { name: /Run send-gate dry-run/i }).hasAttribute("disabled")).toBe(false);
    expect(screen.getByRole("button", { name: /Create mock send intent/i }).hasAttribute("disabled")).toBe(true);
    expect(screen.getByRole("button", { name: /Real email sending disabled/i }).hasAttribute("disabled")).toBe(true);
  });

  it("approves review item through the backend mock API with idempotency and refresh", async () => {
    renderWithTenant(<ReviewQueuePage />);
    fireEvent.click(screen.getByRole("button", { name: /View details for row cccccccc-cccc-cccc-cccc-cccccccccccc/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Approve review/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Approve review/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock review action succeeded/i)).toBeTruthy());
    const fetchMock = vi.mocked(fetch);
    const approveCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc/approve") && init?.method === "POST");
    expect(approveCall).toBeTruthy();
    expect(new Headers(approveCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-review-approve-/);
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc"))).toBe(true);
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/api/v1/review/items"))).toBe(true);
  });

  it("rejects review item through the backend mock API with idempotency", async () => {
    renderWithTenant(<ReviewQueuePage />);
    fireEvent.click(screen.getByRole("button", { name: /View details for row cccccccc-cccc-cccc-cccc-cccccccccccc/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Reject review/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Reject review/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock review action succeeded/i)).toBeTruthy());
    const fetchMock = vi.mocked(fetch);
    const rejectCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc/reject") && init?.method === "POST");
    expect(rejectCall).toBeTruthy();
    expect(new Headers(rejectCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-review-reject-/);
  });

  it("requests review regeneration through the backend mock API with idempotency", async () => {
    renderWithTenant(<ReviewQueuePage />);
    fireEvent.click(screen.getByRole("button", { name: /View details for row cccccccc-cccc-cccc-cccc-cccccccccccc/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /^Request regeneration$/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /^Request regeneration$/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock review action succeeded/i)).toBeTruthy());
    const fetchMock = vi.mocked(fetch);
    const regenCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc/request-regeneration") && init?.method === "POST");
    expect(regenCall).toBeTruthy();
    expect(new Headers(regenCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-review-request-regeneration-/);
  });

  it("runs send-gate dry-run through the backend mock API with idempotency", async () => {
    renderWithTenant(<ReviewQueuePage />);
    fireEvent.click(screen.getByRole("button", { name: /View details for row cccccccc-cccc-cccc-cccc-cccccccccccc/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Run send-gate dry-run/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Run send-gate dry-run/i }));

    await waitFor(() => expect(screen.getByText(/Send-gate dry-run allowed by backend mock API/i)).toBeTruthy());
    expect(screen.getByText(/Status: allowed/i)).toBeTruthy();
    expect(screen.getByText(/Reason: none/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Create mock send intent/i }).hasAttribute("disabled")).toBe(false);

    const fetchMock = vi.mocked(fetch);
    const gateCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/send-gate/dry-run") && init?.method === "POST");
    expect(gateCall).toBeTruthy();
    expect(new Headers(gateCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-send-gate-dry-run-/);
  });

  it("creates mock send intent after send-gate dry-run with idempotency", async () => {
    renderWithTenant(<ReviewQueuePage />);
    fireEvent.click(screen.getByRole("button", { name: /View details for row cccccccc-cccc-cccc-cccc-cccccccccccc/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Run send-gate dry-run/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Run send-gate dry-run/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Create mock send intent/i }).hasAttribute("disabled")).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: /Create mock send intent/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock send intent created/i)).toBeTruthy());
    expect(screen.getByText(/89898989-8989-8989-8989-898989898989/i)).toBeTruthy();
    expect(screen.getByText(/mock_queued/i)).toBeTruthy();
    expect(screen.getAllByText(/No real email was sent/i).length).toBeGreaterThan(0);

    const fetchMock = vi.mocked(fetch);
    const sendIntentCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/send-intents") && init?.method === "POST");
    expect(sendIntentCall).toBeTruthy();
    expect(new Headers(sendIntentCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-send-intents-/);
  });

  it("creates follow-up rule, schedule, and mock-run through backend mock APIs with idempotency", async () => {
    renderWithTenant(<ReviewQueuePage />);
    fireEvent.click(screen.getByRole("button", { name: /View details for row cccccccc-cccc-cccc-cccc-cccccccccccc/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Run send-gate dry-run/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Run send-gate dry-run/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Create mock send intent/i }).hasAttribute("disabled")).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: /Create mock send intent/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Create follow-up rule/i }).hasAttribute("disabled")).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: /Create follow-up rule/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock follow-up rule created/i)).toBeTruthy());
    expect(screen.getByText(/90909090-9090-9090-9090-909090909090/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Create follow-up schedule/i }).hasAttribute("disabled")).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: /Create follow-up schedule/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock follow-up schedule created/i)).toBeTruthy());
    expect(screen.getByText(/a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Run follow-up mock-run/i }).hasAttribute("disabled")).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: /Run follow-up mock-run/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock follow-up mock-run completed/i)).toBeTruthy());
    expect(screen.getByText(/mock_run_complete/i)).toBeTruthy();
    expect(screen.getAllByText(/No real email was sent/i).length).toBeGreaterThan(0);

    const fetchMock = vi.mocked(fetch);
    const ruleCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/followups/rules") && init?.method === "POST");
    const scheduleCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/followups/schedules") && !String(input).includes("mock-run") && init?.method === "POST");
    const mockRunCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/followups/schedules/a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1/mock-run") && init?.method === "POST");
    expect(ruleCall).toBeTruthy();
    expect(scheduleCall).toBeTruthy();
    expect(mockRunCall).toBeTruthy();
    expect(new Headers(ruleCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-followups-rules-/);
    expect(new Headers(scheduleCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-followups-schedules-/);
    expect(new Headers(mockRunCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-followups-schedules-mock-run-/);
  });

  it("shows typed backend follow-up errors without claiming success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path.includes("/api/v1/send-gate/dry-run") && init?.method === "POST") {
          return jsonResponse({ send_gate_result: { id: "78787878-7878-7878-7878-787878787878", draft_id: "66666666-6666-6666-6666-666666666666", status: "allowed", deny_reason_code: null, created_at: "2026-06-24T12:35:00Z", mock_only: true }, idempotency_replay: false, mock_only: true });
        }
        if (path.includes("/api/v1/send-intents") && init?.method === "POST") {
          return jsonResponse({ result: { outbound_message_id: "89898989-8989-8989-8989-898989898989", status: "mock_queued", sent_at: null, mock_only: true }, idempotency_replay: false, mock_only: true });
        }
        if (path.includes("/api/v1/followups/rules") && init?.method === "POST") {
          return jsonResponse({ error: { code: "FOLLOWUP_RULE_DENIED", message: "Follow-up rule denied.", details: { reason: "billing" }, request_id: "req_followup", correlation_id: "corr_followup" } }, 403);
        }
        if (path.includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc")) return jsonResponse({ review_item: { id: "cccccccc-cccc-cccc-cccc-cccccccccccc", draft_id: "66666666-6666-6666-6666-666666666666", campaign_id: "44444444-4444-4444-4444-444444444444", contact_id: "22222222-2222-2222-2222-222222222222", status: "pending_review", reviewer_user_id: "11111111-1111-1111-1111-111111111111", action_reason: null, reviewed_at: null, created_at: "2026-06-24T12:00:00Z", updated_at: "2026-06-24T12:00:00Z" }, mock_only: true });
        if (path.includes("/api/v1/review/items")) return jsonResponse({ review_items: [{ id: "cccccccc-cccc-cccc-cccc-cccccccccccc", draft_id: "66666666-6666-6666-6666-666666666666", campaign_id: "44444444-4444-4444-4444-444444444444", contact_id: "22222222-2222-2222-2222-222222222222", status: "pending_review", reviewer_user_id: null, action_reason: null, reviewed_at: null, created_at: "2026-06-24T12:00:00Z", updated_at: "2026-06-24T12:00:00Z" }], page: { next_cursor: null, limit: 25 }, mock_only: true });
        if (path.includes("/auth/me")) return jsonResponse({ principal: { provider_user_id: "clerk_123", user_id: "11111111-1111-1111-1111-111111111111", email: "owner@example.com", tenant_id: "22222222-2222-2222-2222-222222222222", role: "tenant_owner", membership_version: 1, mfa_verified: true } });
        if (path.includes("/api/v1/billing/access")) return jsonResponse({ access: { is_active: true, can_send: true, can_run_agents: true, can_create_campaign: true, can_export: true, mock_only: true } });
        if (path.includes("/api/v1/billing/subscription")) return jsonResponse({ subscription: { plan: null, tenant_status: "active", grace_until: null, mock_only: true } });
        return jsonResponse({ status: "ok" });
      }),
    );

    renderWithTenant(<ReviewQueuePage />);
    fireEvent.click(screen.getByRole("button", { name: /View details for row cccccccc-cccc-cccc-cccc-cccccccccccc/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Run send-gate dry-run/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Run send-gate dry-run/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Create mock send intent/i }).hasAttribute("disabled")).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: /Create mock send intent/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Create follow-up rule/i }).hasAttribute("disabled")).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: /Create follow-up rule/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock follow-up action failed safely/i)).toBeTruthy());
    expect(screen.getByText(/Follow-up rule denied/i)).toBeTruthy();
    expect(screen.getByText(/FOLLOWUP_RULE_DENIED/i)).toBeTruthy();
    expect(screen.queryByText(/Backend mock follow-up rule created/i)).toBeNull();
  });

  it("shows NETWORK_ERROR follow-up mock-run failure without claiming success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path.includes("/api/v1/send-gate/dry-run") && init?.method === "POST") return jsonResponse({ send_gate_result: { id: "78787878-7878-7878-7878-787878787878", draft_id: "66666666-6666-6666-6666-666666666666", status: "allowed", deny_reason_code: null, created_at: "2026-06-24T12:35:00Z", mock_only: true }, idempotency_replay: false, mock_only: true });
        if (path.includes("/api/v1/send-intents") && init?.method === "POST") return jsonResponse({ result: { outbound_message_id: "89898989-8989-8989-8989-898989898989", status: "mock_queued", sent_at: null, mock_only: true }, idempotency_replay: false, mock_only: true });
        if (path.includes("/api/v1/followups/rules") && init?.method === "POST") return jsonResponse({ followup_rule: { id: "90909090-9090-9090-9090-909090909090", campaign_id: "44444444-4444-4444-4444-444444444444", delay_seconds: 86400, created_at: "2026-06-24T12:36:00Z", updated_at: "2026-06-24T12:36:00Z", mock_only: true }, idempotency_replay: false, mock_only: true });
        if (path.includes("/api/v1/followups/schedules/a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1/mock-run") && init?.method === "POST") throw new Error("backend unavailable");
        if (path.includes("/api/v1/followups/schedules") && init?.method === "POST") return jsonResponse({ followup_schedule: { id: "a1a1a1a1-a1a1-a1a1-a1a1-a1a1a1a1a1a1", campaign_id: "44444444-4444-4444-4444-444444444444", contact_id: "22222222-2222-2222-2222-222222222222", original_outbound_message_id: "89898989-8989-8989-8989-898989898989", original_draft_id: "66666666-6666-6666-6666-666666666666", followup_rule_id: "90909090-9090-9090-9090-909090909090", status: "scheduled", run_after: "2026-06-25T12:35:00Z", created_at: "2026-06-24T12:37:00Z", updated_at: "2026-06-24T12:37:00Z", mock_only: true }, idempotency_replay: false, mock_only: true });
        if (path.includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc")) return jsonResponse({ review_item: { id: "cccccccc-cccc-cccc-cccc-cccccccccccc", draft_id: "66666666-6666-6666-6666-666666666666", campaign_id: "44444444-4444-4444-4444-444444444444", contact_id: "22222222-2222-2222-2222-222222222222", status: "pending_review", reviewer_user_id: "11111111-1111-1111-1111-111111111111", action_reason: null, reviewed_at: null, created_at: "2026-06-24T12:00:00Z", updated_at: "2026-06-24T12:00:00Z" }, mock_only: true });
        if (path.includes("/api/v1/review/items")) return jsonResponse({ review_items: [{ id: "cccccccc-cccc-cccc-cccc-cccccccccccc", draft_id: "66666666-6666-6666-6666-666666666666", campaign_id: "44444444-4444-4444-4444-444444444444", contact_id: "22222222-2222-2222-2222-222222222222", status: "pending_review", reviewer_user_id: null, action_reason: null, reviewed_at: null, created_at: "2026-06-24T12:00:00Z", updated_at: "2026-06-24T12:00:00Z" }], page: { next_cursor: null, limit: 25 }, mock_only: true });
        if (path.includes("/auth/me")) return jsonResponse({ principal: { provider_user_id: "clerk_123", user_id: "11111111-1111-1111-1111-111111111111", email: "owner@example.com", tenant_id: "22222222-2222-2222-2222-222222222222", role: "tenant_owner", membership_version: 1, mfa_verified: true } });
        if (path.includes("/api/v1/billing/access")) return jsonResponse({ access: { is_active: true, can_send: true, can_run_agents: true, can_create_campaign: true, can_export: true, mock_only: true } });
        if (path.includes("/api/v1/billing/subscription")) return jsonResponse({ subscription: { plan: null, tenant_status: "active", grace_until: null, mock_only: true } });
        return jsonResponse({ status: "ok" });
      }),
    );

    renderWithTenant(<ReviewQueuePage />);
    fireEvent.click(screen.getByRole("button", { name: /View details for row cccccccc-cccc-cccc-cccc-cccccccccccc/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Run send-gate dry-run/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Run send-gate dry-run/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Create mock send intent/i }).hasAttribute("disabled")).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: /Create mock send intent/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Create follow-up rule/i }).hasAttribute("disabled")).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: /Create follow-up rule/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Create follow-up schedule/i }).hasAttribute("disabled")).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: /Create follow-up schedule/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Run follow-up mock-run/i }).hasAttribute("disabled")).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: /Run follow-up mock-run/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock follow-up action failed safely/i)).toBeTruthy());
    expect(screen.getByText(/NETWORK_ERROR/i)).toBeTruthy();
    expect(screen.queryByText(/Backend mock follow-up mock-run completed/i)).toBeNull();
  });

  it("shows typed backend send-gate errors without claiming success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path.includes("/api/v1/send-gate/dry-run") && init?.method === "POST") {
          return jsonResponse({ error: { code: "SEND_GATE_DENIED", message: "Send gate dry-run denied.", details: { reason: "suppression" }, request_id: "req_send_gate", correlation_id: "corr_send_gate" } }, 403);
        }
        if (path.includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc")) {
          return jsonResponse({ review_item: { id: "cccccccc-cccc-cccc-cccc-cccccccccccc", draft_id: "66666666-6666-6666-6666-666666666666", campaign_id: "44444444-4444-4444-4444-444444444444", contact_id: "22222222-2222-2222-2222-222222222222", status: "pending_review", reviewer_user_id: "11111111-1111-1111-1111-111111111111", action_reason: null, reviewed_at: null, created_at: "2026-06-24T12:00:00Z", updated_at: "2026-06-24T12:00:00Z" }, mock_only: true });
        }
        if (path.includes("/api/v1/review/items")) {
          return jsonResponse({ review_items: [{ id: "cccccccc-cccc-cccc-cccc-cccccccccccc", draft_id: "66666666-6666-6666-6666-666666666666", campaign_id: "44444444-4444-4444-4444-444444444444", contact_id: "22222222-2222-2222-2222-222222222222", status: "pending_review", reviewer_user_id: null, action_reason: null, reviewed_at: null, created_at: "2026-06-24T12:00:00Z", updated_at: "2026-06-24T12:00:00Z" }], page: { next_cursor: null, limit: 25 }, mock_only: true });
        }
        if (path.includes("/auth/me")) return jsonResponse({ principal: { provider_user_id: "clerk_123", user_id: "11111111-1111-1111-1111-111111111111", email: "owner@example.com", tenant_id: "22222222-2222-2222-2222-222222222222", role: "tenant_owner", membership_version: 1, mfa_verified: true } });
        if (path.includes("/api/v1/billing/access")) return jsonResponse({ access: { is_active: true, can_send: true, can_run_agents: true, can_create_campaign: true, can_export: true, mock_only: true } });
        if (path.includes("/api/v1/billing/subscription")) return jsonResponse({ subscription: { plan: null, tenant_status: "active", grace_until: null, mock_only: true } });
        return jsonResponse({ status: "ok" });
      }),
    );

    renderWithTenant(<ReviewQueuePage />);
    fireEvent.click(screen.getByRole("button", { name: /View details for row cccccccc-cccc-cccc-cccc-cccccccccccc/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Run send-gate dry-run/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Run send-gate dry-run/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock send action failed safely/i)).toBeTruthy());
    expect(screen.getByText(/Send gate dry-run denied/i)).toBeTruthy();
    expect(screen.getByText(/SEND_GATE_DENIED/i)).toBeTruthy();
    expect(screen.queryByText(/Backend mock send intent created/i)).toBeNull();
  });

  it("shows NETWORK_ERROR mock send intent failure without claiming success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path.includes("/api/v1/send-gate/dry-run") && init?.method === "POST") {
          return jsonResponse({ send_gate_result: { id: "78787878-7878-7878-7878-787878787878", draft_id: "66666666-6666-6666-6666-666666666666", status: "allowed", deny_reason_code: null, created_at: "2026-06-24T12:35:00Z", mock_only: true }, idempotency_replay: false, mock_only: true });
        }
        if (path.includes("/api/v1/send-intents") && init?.method === "POST") throw new Error("backend unavailable");
        if (path.includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc")) {
          return jsonResponse({ review_item: { id: "cccccccc-cccc-cccc-cccc-cccccccccccc", draft_id: "66666666-6666-6666-6666-666666666666", campaign_id: "44444444-4444-4444-4444-444444444444", contact_id: "22222222-2222-2222-2222-222222222222", status: "pending_review", reviewer_user_id: "11111111-1111-1111-1111-111111111111", action_reason: null, reviewed_at: null, created_at: "2026-06-24T12:00:00Z", updated_at: "2026-06-24T12:00:00Z" }, mock_only: true });
        }
        if (path.includes("/api/v1/review/items")) {
          return jsonResponse({ review_items: [{ id: "cccccccc-cccc-cccc-cccc-cccccccccccc", draft_id: "66666666-6666-6666-6666-666666666666", campaign_id: "44444444-4444-4444-4444-444444444444", contact_id: "22222222-2222-2222-2222-222222222222", status: "pending_review", reviewer_user_id: null, action_reason: null, reviewed_at: null, created_at: "2026-06-24T12:00:00Z", updated_at: "2026-06-24T12:00:00Z" }], page: { next_cursor: null, limit: 25 }, mock_only: true });
        }
        if (path.includes("/auth/me")) return jsonResponse({ principal: { provider_user_id: "clerk_123", user_id: "11111111-1111-1111-1111-111111111111", email: "owner@example.com", tenant_id: "22222222-2222-2222-2222-222222222222", role: "tenant_owner", membership_version: 1, mfa_verified: true } });
        if (path.includes("/api/v1/billing/access")) return jsonResponse({ access: { is_active: true, can_send: true, can_run_agents: true, can_create_campaign: true, can_export: true, mock_only: true } });
        if (path.includes("/api/v1/billing/subscription")) return jsonResponse({ subscription: { plan: null, tenant_status: "active", grace_until: null, mock_only: true } });
        return jsonResponse({ status: "ok" });
      }),
    );

    renderWithTenant(<ReviewQueuePage />);
    fireEvent.click(screen.getByRole("button", { name: /View details for row cccccccc-cccc-cccc-cccc-cccccccccccc/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Run send-gate dry-run/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Run send-gate dry-run/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Create mock send intent/i }).hasAttribute("disabled")).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: /Create mock send intent/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock send action failed safely/i)).toBeTruthy());
    expect(screen.getByText(/NETWORK_ERROR/i)).toBeTruthy();
    expect(screen.queryByText(/Backend mock send intent created/i)).toBeNull();
  });

  it("shows typed backend review action errors without claiming success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path.includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc/approve") && init?.method === "POST") {
          return jsonResponse(
            {
              error: {
                code: "REVIEW_ACTION_DENIED",
                message: "Review action denied.",
                details: { gate: "groundedness" },
                request_id: "req_review_action",
                correlation_id: "corr_review_action",
              },
            },
            403,
          );
        }
        if (path.includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc")) {
          return jsonResponse({ review_item: { id: "cccccccc-cccc-cccc-cccc-cccccccccccc", draft_id: "66666666-6666-6666-6666-666666666666", campaign_id: "44444444-4444-4444-4444-444444444444", contact_id: "22222222-2222-2222-2222-222222222222", status: "pending_review", reviewer_user_id: "11111111-1111-1111-1111-111111111111", action_reason: null, reviewed_at: null, created_at: "2026-06-24T12:00:00Z", updated_at: "2026-06-24T12:00:00Z" }, mock_only: true });
        }
        if (path.includes("/api/v1/review/items")) {
          return jsonResponse({ review_items: [{ id: "cccccccc-cccc-cccc-cccc-cccccccccccc", draft_id: "66666666-6666-6666-6666-666666666666", campaign_id: "44444444-4444-4444-4444-444444444444", contact_id: "22222222-2222-2222-2222-222222222222", status: "pending_review", reviewer_user_id: null, action_reason: null, reviewed_at: null, created_at: "2026-06-24T12:00:00Z", updated_at: "2026-06-24T12:00:00Z" }], page: { next_cursor: null, limit: 25 }, mock_only: true });
        }
        if (path.includes("/auth/me")) {
          return jsonResponse({ principal: { provider_user_id: "clerk_123", user_id: "11111111-1111-1111-1111-111111111111", email: "owner@example.com", tenant_id: "22222222-2222-2222-2222-222222222222", role: "tenant_owner", membership_version: 1, mfa_verified: true } });
        }
        if (path.includes("/api/v1/billing/access")) {
          return jsonResponse({ access: { is_active: true, can_send: true, can_run_agents: true, can_create_campaign: true, can_export: true, mock_only: true } });
        }
        if (path.includes("/api/v1/billing/subscription")) {
          return jsonResponse({ subscription: { plan: null, tenant_status: "active", grace_until: null, mock_only: true } });
        }
        return jsonResponse({ status: "ok" });
      }),
    );

    renderWithTenant(<ReviewQueuePage />);
    fireEvent.click(screen.getByRole("button", { name: /View details for row cccccccc-cccc-cccc-cccc-cccccccccccc/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Approve review/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Approve review/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock review action failed safely/i)).toBeTruthy());
    expect(screen.getByText(/Review action denied/i)).toBeTruthy();
    expect(screen.getByText(/REVIEW_ACTION_DENIED/i)).toBeTruthy();
    expect(screen.queryByText(/Backend mock review action succeeded/i)).toBeNull();
  });

  it("shows NETWORK_ERROR review action failure without claiming success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path.includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc/reject") && init?.method === "POST") throw new Error("backend unavailable");
        if (path.includes("/api/v1/review/items/cccccccc-cccc-cccc-cccc-cccccccccccc")) {
          return jsonResponse({ review_item: { id: "cccccccc-cccc-cccc-cccc-cccccccccccc", draft_id: "66666666-6666-6666-6666-666666666666", campaign_id: "44444444-4444-4444-4444-444444444444", contact_id: "22222222-2222-2222-2222-222222222222", status: "pending_review", reviewer_user_id: "11111111-1111-1111-1111-111111111111", action_reason: null, reviewed_at: null, created_at: "2026-06-24T12:00:00Z", updated_at: "2026-06-24T12:00:00Z" }, mock_only: true });
        }
        if (path.includes("/api/v1/review/items")) {
          return jsonResponse({ review_items: [{ id: "cccccccc-cccc-cccc-cccc-cccccccccccc", draft_id: "66666666-6666-6666-6666-666666666666", campaign_id: "44444444-4444-4444-4444-444444444444", contact_id: "22222222-2222-2222-2222-222222222222", status: "pending_review", reviewer_user_id: null, action_reason: null, reviewed_at: null, created_at: "2026-06-24T12:00:00Z", updated_at: "2026-06-24T12:00:00Z" }], page: { next_cursor: null, limit: 25 }, mock_only: true });
        }
        if (path.includes("/auth/me")) {
          return jsonResponse({ principal: { provider_user_id: "clerk_123", user_id: "11111111-1111-1111-1111-111111111111", email: "owner@example.com", tenant_id: "22222222-2222-2222-2222-222222222222", role: "tenant_owner", membership_version: 1, mfa_verified: true } });
        }
        if (path.includes("/api/v1/billing/access")) {
          return jsonResponse({ access: { is_active: true, can_send: true, can_run_agents: true, can_create_campaign: true, can_export: true, mock_only: true } });
        }
        if (path.includes("/api/v1/billing/subscription")) {
          return jsonResponse({ subscription: { plan: null, tenant_status: "active", grace_until: null, mock_only: true } });
        }
        return jsonResponse({ status: "ok" });
      }),
    );

    renderWithTenant(<ReviewQueuePage />);
    fireEvent.click(screen.getByRole("button", { name: /View details for row cccccccc-cccc-cccc-cccc-cccccccccccc/i }));
    await waitFor(() => expect(screen.getByRole("button", { name: /Reject review/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Reject review/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock review action failed safely/i)).toBeTruthy());
    expect(screen.getByText(/NETWORK_ERROR/i)).toBeTruthy();
    expect(screen.queryByText(/Backend mock review action succeeded/i)).toBeNull();
  });

  it("renders review fixture fallback when backend is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("backend unavailable"); }));
    renderWithTenant(<ReviewQueuePage />);

    await waitFor(() => expect(screen.getAllByText(/fixture fallback/i).length).toBeGreaterThan(0));
    expect(screen.getByText(/CRE Multifamily Owner Outreach/i)).toBeTruthy();
    expect(screen.getByText(/No real sending/i)).toBeTruthy();
  });

  it("strict backend mode shows review backend error instead of fixture rows", async () => {
    process.env["NEXT_PUBLIC_" + "STRICT_BACKEND_MODE"] = "true";
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("backend unavailable"); }));
    renderWithTenant(<ReviewQueuePage />);

    await waitFor(() => expect(screen.getByText(/Strict backend mode: review queue unavailable/i)).toBeTruthy());
    expect(screen.getByText(/Review queue backend mock API read failed/i)).toBeTruthy();
    expect(screen.getByText(/Local\/mock MVP only/i)).toBeTruthy();
    expect(screen.queryByText(/Approve in workspace/i)).toBeNull();
  });

  it("renders the deliverability dashboard shell", async () => {
    renderWithTenant(<DeliverabilityPage />);
    expect(screen.getByRole("heading", { name: /deliverability/i })).toBeTruthy();
    expect(screen.getByText(/Local\/mock MVP only/i)).toBeTruthy();
    await waitFor(() => expect(screen.getAllByText(/backend mock API/i).length).toBeGreaterThan(0));
    expect(screen.getAllByText(/Mailbox health/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/example.test/i)).toBeTruthy();
    expect(screen.getByText(/Deliverability API read-only/i)).toBeTruthy();
    expect(screen.getByText(/No real DNS checks/i)).toBeTruthy();
    expect(screen.getByText(/No provider calls/i)).toBeTruthy();
    expect(screen.getAllByText(/No real sending/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Update throttle/i }).hasAttribute("disabled")).toBe(true);
    expect(screen.getByRole("button", { name: /Pause sending/i }).hasAttribute("disabled")).toBe(true);
  });

  it("renders deliverability fixture fallback when backend is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("backend unavailable"); }));
    renderWithTenant(<DeliverabilityPage />);

    await waitFor(() => expect(screen.getAllByText(/fixture fallback/i).length).toBeGreaterThan(0));
    expect(screen.getByText(/owner-demo@example.com/i)).toBeTruthy();
    expect(screen.getByText(/No real DNS checks/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Update throttle/i }).hasAttribute("disabled")).toBe(true);
  });

  it("renders the outcomes ROI dashboard shell", async () => {
    renderWithTenant(<OutcomesPage />);
    expect(screen.getByRole("heading", { name: /outcomes and ROI/i })).toBeTruthy();
    expect(screen.getByText(/Local\/mock MVP only/i)).toBeTruthy();
    await waitFor(() => expect(screen.getAllByText(/backend mock API/i).length).toBeGreaterThan(0));
    expect(screen.getByRole("table", { name: /campaign outcomes demo table/i })).toBeTruthy();
    expect(screen.getByText(/Outcomes API read-only/i)).toBeTruthy();
    expect(screen.getByText(/No real Stripe\/payment data/i)).toBeTruthy();
    expect(screen.getByText(/No CRM sync/i)).toBeTruthy();
    expect(screen.getByText(/No live attribution/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Export outcomes/i }).hasAttribute("disabled")).toBe(true);
    expect(screen.getByRole("button", { name: /Sync CRM/i }).hasAttribute("disabled")).toBe(true);
    expect(screen.getAllByRole("button", { name: /Recalculate/i }).every((button) => button.hasAttribute("disabled"))).toBe(true);
  });

  it("renders outcomes fixture fallback when backend is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("backend unavailable"); }));
    renderWithTenant(<OutcomesPage />);

    await waitFor(() => expect(screen.getAllByText(/fixture fallback/i).length).toBeGreaterThan(0));
    expect(screen.getByText(/CRE Multifamily Owner Outreach/i)).toBeTruthy();
    expect(screen.getByText(/No real Stripe\/payment data/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /Export outcomes/i }).hasAttribute("disabled")).toBe(true);
  });

  it("renders the settings hub shell", () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <SettingsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );
    expect(screen.getByRole("heading", { name: /^settings$/i })).toBeTruthy();
    expect(screen.getAllByText(/Tenant profile settings/i).length).toBeGreaterThan(0);
  });

  it("updates tenant settings through the backend mock API with idempotency", async () => {
    renderWithTenant(<SettingsPage />);
    await waitFor(() => expect(screen.getByRole("button", { name: /Save local\/mock tenant settings/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Save local\/mock tenant settings/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock tenant settings update succeeded/i)).toBeTruthy());
    expect(screen.getAllByText(/No provider sync/i).length).toBeGreaterThan(0);

    const fetchMock = vi.mocked(fetch);
    const updateCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/tenants/current") && init?.method === "PATCH");
    expect(updateCall).toBeTruthy();
    expect(new Headers(updateCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-tenants-current-update-/);
  });

  it("shows typed backend tenant settings errors without claiming success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path.includes("/api/v1/tenants/current") && init?.method === "PATCH") {
          return jsonResponse({ error: { code: "TENANT_UPDATE_DENIED", message: "Tenant update denied.", request_id: "req_tenant_update", correlation_id: "corr_tenant_update" } }, 403);
        }
        if (path.includes("/api/v1/tenants/current")) return jsonResponse({ tenant: { id: "22222222-2222-2222-2222-222222222222", name: "Automated Structure Test Tenant", status: "active", settings: { timezone: "UTC", locale: "en-US" }, created_at: "2026-06-24T12:00:00Z", updated_at: "2026-06-24T12:00:00Z", mock_only: true }, mock_only: true });
        if (path.includes("/auth/me")) return jsonResponse({ principal: { provider_user_id: "clerk_123", user_id: "11111111-1111-1111-1111-111111111111", email: "owner@example.com", tenant_id: "22222222-2222-2222-2222-222222222222", role: "tenant_owner", membership_version: 1, mfa_verified: true } });
        if (path.includes("/api/v1/billing/access")) return jsonResponse({ access: { is_active: true, can_send: true, can_run_agents: true, can_create_campaign: true, can_export: true, mock_only: true } });
        if (path.includes("/api/v1/billing/subscription")) return jsonResponse({ subscription: { plan: null, tenant_status: "active", grace_until: null, mock_only: true } });
        return jsonResponse({ status: "ok" });
      }),
    );

    renderWithTenant(<SettingsPage />);
    await waitFor(() => expect(screen.getByRole("button", { name: /Save local\/mock tenant settings/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Save local\/mock tenant settings/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock tenant settings update failed safely/i)).toBeTruthy());
    expect(screen.getByText(/Tenant update denied/i)).toBeTruthy();
    expect(screen.getByText(/TENANT_UPDATE_DENIED/i)).toBeTruthy();
    expect(screen.queryByText(/Backend mock tenant settings update succeeded/i)).toBeNull();
  });

  it("renders team settings table shell", () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <TeamSettingsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );
    expect(screen.getByRole("heading", { name: /team settings/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /team members table/i })).toBeTruthy();
  });

  it("renders integrations settings shell", () => {
    render(<IntegrationsSettingsPage />);
    expect(screen.getByRole("heading", { name: /integrations/i })).toBeTruthy();
    expect(screen.getByText(/No real provider\/OAuth calls/i)).toBeTruthy();
  });

  it("renders security settings shell", () => {
    render(<SecuritySettingsPage />);
    expect(screen.getByRole("heading", { name: /security settings/i })).toBeTruthy();
    expect(screen.getAllByText(/Production JWT verifier/i).length).toBeGreaterThan(0);
  });

  it("renders compliance settings shell", () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <ComplianceSettingsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );
    expect(screen.getByRole("heading", { name: /compliance settings/i })).toBeTruthy();
    expect(screen.getByText(/US-first baseline/i)).toBeTruthy();
  });

  it("loads compliance settings from the backend mock API while provider actions stay locked", async () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <ComplianceSettingsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );

    await waitFor(() => expect(screen.getByText(/Compliance profile loaded from backend mock API/i)).toBeTruthy());
    expect(screen.getByText(/Compliance mock update/i)).toBeTruthy();
    expect(screen.getByText(/No real sending/i)).toBeTruthy();
    expect(screen.getAllByText(/No provider sync/i).length).toBeGreaterThan(0);
  });

  it("updates compliance profile through the backend mock API with idempotency", async () => {
    renderWithTenant(<ComplianceSettingsPage />);
    await waitFor(() => expect(screen.getByRole("button", { name: /Update local\/mock compliance profile/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Update local\/mock compliance profile/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock compliance profile update succeeded/i)).toBeTruthy());
    expect(screen.getByText(/No provider sync, real webhook, live sending, SMS, or production compliance automation was triggered/i)).toBeTruthy();

    const fetchMock = vi.mocked(fetch);
    const updateCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/compliance/profile") && init?.method === "PUT");
    expect(updateCall).toBeTruthy();
    expect(new Headers(updateCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-compliance-profile-update-/);
  });

  it("renders compliance fixture fallback when backend auth is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("backend unavailable"); }));
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <ComplianceSettingsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );

    await waitFor(() => expect(screen.getByText(/Backend unavailable or auth missing/i)).toBeTruthy());
  });

  it("renders suppression settings table shell", () => {
    renderWithTenant(<SuppressionSettingsPage />);
    expect(screen.getByRole("heading", { name: /suppression settings/i })).toBeTruthy();
    expect(screen.getByRole("table", { name: /suppression demo table/i })).toBeTruthy();
  });

  it("loads suppressions from the backend mock API while provider actions stay locked", async () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <SuppressionSettingsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );

    await waitFor(() => expect(screen.getByText(/manual backend mock block/i)).toBeTruthy());
    expect(screen.getAllByText(/Suppression mock actions/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/No provider sync/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Provider sync locked/i }).hasAttribute("disabled")).toBe(true);
  });

  it("creates suppression through the backend mock API with idempotency", async () => {
    renderWithTenant(<SuppressionSettingsPage />);
    await waitFor(() => expect(screen.getByRole("button", { name: /Create local\/mock suppression/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Create local\/mock suppression/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock suppression created/i)).toBeTruthy());
    expect(screen.getByText(/eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee/i)).toBeTruthy();

    const fetchMock = vi.mocked(fetch);
    const createCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/suppressions") && !String(input).includes("/reinstate") && init?.method === "POST");
    expect(createCall).toBeTruthy();
    expect(new Headers(createCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-suppressions-create-/);
  });

  it("reinstates suppression through the backend mock API with idempotency", async () => {
    renderWithTenant(<SuppressionSettingsPage />);
    await waitFor(() => expect(screen.getByRole("button", { name: /Reinstate local\/mock suppression/i }).hasAttribute("disabled")).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: /Reinstate local\/mock suppression/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock suppression reinstated/i)).toBeTruthy());
    expect(screen.getAllByText(/dddddddd-dddd-dddd-dddd-dddddddddddd/i).length).toBeGreaterThan(0);

    const fetchMock = vi.mocked(fetch);
    const reinstateCall = fetchMock.mock.calls.find(([input, init]) => String(input).includes("/api/v1/suppressions/dddddddd-dddd-dddd-dddd-dddddddddddd/reinstate") && init?.method === "POST");
    expect(reinstateCall).toBeTruthy();
    expect(new Headers(reinstateCall?.[1]?.headers).get("Idempotency-Key")).toMatch(/^as-suppressions-reinstate-/);
  });

  it("shows NETWORK_ERROR suppression create failure without claiming success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = String(input);
        if (path.includes("/api/v1/suppressions") && init?.method === "POST") throw new Error("backend unavailable");
        if (path.includes("/api/v1/suppressions")) return jsonResponse({ suppressions: [{ id: "dddddddd-dddd-dddd-dddd-dddddddddddd", channel: "email", reason: "manual backend mock block", source: "mock_api", never_contact: true, created_at: "2026-06-24T12:00:00Z", revoked_at: null, active: true, mock_only: true }], page: { next_cursor: null, limit: 25 }, mock_only: true });
        if (path.includes("/auth/me")) return jsonResponse({ principal: { provider_user_id: "clerk_123", user_id: "11111111-1111-1111-1111-111111111111", email: "owner@example.com", tenant_id: "22222222-2222-2222-2222-222222222222", role: "tenant_owner", membership_version: 1, mfa_verified: true } });
        if (path.includes("/api/v1/billing/access")) return jsonResponse({ access: { is_active: true, can_send: true, can_run_agents: true, can_create_campaign: true, can_export: true, mock_only: true } });
        if (path.includes("/api/v1/billing/subscription")) return jsonResponse({ subscription: { plan: null, tenant_status: "active", grace_until: null, mock_only: true } });
        return jsonResponse({ status: "ok" });
      }),
    );

    renderWithTenant(<SuppressionSettingsPage />);
    await waitFor(() => expect(screen.getByRole("button", { name: /Create local\/mock suppression/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Create local\/mock suppression/i }));

    await waitFor(() => expect(screen.getByText(/Backend mock suppression action failed safely/i)).toBeTruthy());
    expect(screen.getByText(/NETWORK_ERROR/i)).toBeTruthy();
    expect(screen.queryByText(/Backend mock suppression created/i)).toBeNull();
  });

  it("renders suppression fixture fallback when backend is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("backend unavailable"); }));
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider initialTenantId="22222222-2222-2222-2222-222222222222">
          <SuppressionSettingsPage />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );

    await waitFor(() => expect(screen.getByText(/fixture fallback/i)).toBeTruthy());
    expect(screen.getByText(/suppressed-demo@example.com/i)).toBeTruthy();
  });
});

describe("phase 0 frontend wiring components", () => {
  it("proves local/mock auth is not allowed in production by default", () => {
    expect(isLocalMockAuthAllowed("production", undefined)).toBe(false);
    expect(isLocalMockAuthAllowed("production", "true")).toBe(true);
    expect(isLocalMockAuthAllowed("development", undefined)).toBe(true);
  });

  it("protects app routes when Clerk auth is not signed in", () => {
    render(
      <ClerkFrontendProvider>
        <AuthGate>
          <div>Protected content</div>
        </AuthGate>
      </ClerkFrontendProvider>,
    );
    expect(screen.getByText(/authentication required/i)).toBeTruthy();
    expect(screen.queryByText(/protected content/i)).toBeNull();
  });

  it("shows session unavailable when auth is not signed in", async () => {
    render(
      <ClerkFrontendProvider>
        <TenantProvider initialTenantId="11111111-1111-1111-1111-111111111111">
          <TenantStatusCard />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );
    await waitFor(() => expect(screen.getByText(/session unavailable/i)).toBeTruthy());
  });

  it("loads tenant context from /auth/me when auth shell is signed in", async () => {
    render(
      <ClerkFrontendProvider value={signedInAuth}>
        <TenantProvider>
          <TenantStatusCard />
        </TenantProvider>
      </ClerkFrontendProvider>,
    );

    await waitFor(() => expect(screen.getByText(/tenant access confirmed/i)).toBeTruthy());
    expect(screen.getByText(/tenant_owner/i)).toBeTruthy();
  });

  it("shows central billing gates in locked/read-only mode", () => {
    render(<BillingBanner status={readOnlyBillingStatus} />);
    expect(screen.getByText(/billing: unknown/i)).toBeTruthy();
    expect(screen.getAllByText(/locked/i).length).toBeGreaterThan(0);
  });

  it("only formats safe audit detail keys", () => {
    expect(formatSafeDetails({ scope: "read:audit", token: "sentinel", contact_hash: "hash" })).toBe(
      "scope: read:audit",
    );
  });

  it("renders audit denied state safely", () => {
    render(<AuditLogTable events={[]} state="denied" />);
    expect(screen.getByText(/access denied/i)).toBeTruthy();
  });

  it("login page shows demo login button in local/mock mode after hydration", async () => {
    render(
      <ClerkFrontendProvider>
        <LoginPage />
      </ClerkFrontendProvider>,
    );
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Continue with Demo Account/i })).toBeTruthy(),
    );
    expect(screen.getByText(/Local\/mock mode · No real credentials required/i)).toBeTruthy();
  });

  it("login page does not show demo login button when mockSignIn is absent", () => {
    const noMockSignInAuth: FrontendAuthState = {
      isLoaded: true,
      isSignedIn: false,
      userId: null,
      email: null,
      tenantId: null,
      mode: "local_mock",
      getToken: async () => null,
    };
    render(
      <ClerkFrontendProvider value={noMockSignInAuth}>
        <LoginPage />
      </ClerkFrontendProvider>,
    );
    expect(screen.queryByRole("button", { name: /Continue with Demo Account/i })).toBeNull();
    expect(screen.queryByText(/No real credentials required/i)).toBeNull();
  });
});
