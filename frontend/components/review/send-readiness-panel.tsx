"use client";

import { useState } from "react";
import { AlertCircle, CalendarClock, CheckCircle2, Loader2, MailCheck, Send, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { createFollowUpRule, createFollowUpSchedule, createSendIntent, mockRunFollowUpSchedule, runSendGateDryRun } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";
import type { ReviewItem } from "./review-sample-data";

type ActionState = "idle" | "submitting" | "success" | "error";
type ErrorScope = "send" | "followup";

type GateSummary = {
  id: string;
  status: string;
  denyReason: string | null;
  mockOnly: boolean;
};

type MockSendSummary = {
  outboundMessageId: string;
  status: string;
  sentAt: string | null;
  mockOnly: boolean;
};

type FollowUpRuleSummary = {
  id: string;
  campaignId: string;
  delaySeconds: number;
  mockOnly: boolean;
};

type FollowUpScheduleSummary = {
  id: string;
  status: string;
  runAfter: string;
  originalOutboundMessageId: string;
  mockOnly: boolean;
};

const FALLBACK_CAMPAIGN_ID = "44444444-4444-4444-4444-444444444444";
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function isGateAllowed(status: string): boolean {
  return ["allowed", "passed", "approved", "ready"].includes(status.toLowerCase());
}

function campaignIdForFollowUp(item: ReviewItem): string {
  return UUID_RE.test(item.draft.campaignId) ? item.draft.campaignId : FALLBACK_CAMPAIGN_ID;
}

export function SendReadinessPanel({ item }: { item: ReviewItem }) {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const [gateState, setGateState] = useState<ActionState>("idle");
  const [sendState, setSendState] = useState<ActionState>("idle");
  const [ruleState, setRuleState] = useState<ActionState>("idle");
  const [scheduleState, setScheduleState] = useState<ActionState>("idle");
  const [mockRunState, setMockRunState] = useState<ActionState>("idle");
  const [gate, setGate] = useState<GateSummary | null>(null);
  const [mockSend, setMockSend] = useState<MockSendSummary | null>(null);
  const [followUpRule, setFollowUpRule] = useState<FollowUpRuleSummary | null>(null);
  const [followUpSchedule, setFollowUpSchedule] = useState<FollowUpScheduleSummary | null>(null);
  const [mockRunSchedule, setMockRunSchedule] = useState<FollowUpScheduleSummary | null>(null);
  const [error, setError] = useState<{ scope: ErrorScope; message: string; code: string; requestId: string | null } | null>(null);
  const canAct = auth.isLoaded && auth.isSignedIn && Boolean(selectedTenantId);
  const gateAllowed = gate ? isGateAllowed(gate.status) : false;
  const followUpBusy = ruleState === "submitting" || scheduleState === "submitting" || mockRunState === "submitting";

  function authOptions(tenantId: string) {
    return {
      getToken: auth.getToken,
      getTenantId: () => tenantId,
    };
  }

  function setSafeError(scope: ErrorScope, err: unknown, fallback: string) {
    if (err instanceof ApiError) {
      setError({ scope, message: err.message, code: err.code, requestId: err.requestId });
    } else {
      setError({ scope, message: fallback, code: "UNKNOWN", requestId: null });
    }
  }

  async function handleDryRun() {
    if (!canAct || !selectedTenantId || gateState === "submitting") return;

    setGateState("submitting");
    setSendState("idle");
    setRuleState("idle");
    setScheduleState("idle");
    setMockRunState("idle");
    setGate(null);
    setMockSend(null);
    setFollowUpRule(null);
    setFollowUpSchedule(null);
    setMockRunSchedule(null);
    setError(null);

    try {
      const res = await runSendGateDryRun(authOptions(selectedTenantId), { draft_id: item.draft.id });
      if (!res.send_gate_result) {
        setError({ scope: "send", message: "The backend mock API did not return a send-gate result. No success was recorded.", code: "SEND_GATE_RESULT_MISSING", requestId: null });
        setGateState("error");
        return;
      }
      setGate({
        id: res.send_gate_result.id,
        status: res.send_gate_result.status,
        denyReason: res.send_gate_result.deny_reason_code ?? null,
        mockOnly: Boolean(res.mock_only ?? res.send_gate_result.mock_only),
      });
      setGateState("success");
    } catch (err) {
      setSafeError("send", err, "The local/mock send-gate dry-run failed safely. No send intent was created.");
      setGateState("error");
    }
  }

  async function handleMockSendIntent() {
    if (!canAct || !selectedTenantId || !gateAllowed || sendState === "submitting") return;

    setSendState("submitting");
    setRuleState("idle");
    setScheduleState("idle");
    setMockRunState("idle");
    setMockSend(null);
    setFollowUpRule(null);
    setFollowUpSchedule(null);
    setMockRunSchedule(null);
    setError(null);

    try {
      const res = await createSendIntent(authOptions(selectedTenantId), { draft_id: item.draft.id });
      if (!res.result) {
        setError({ scope: "send", message: "The backend mock API did not return a mock send intent result. No success was recorded.", code: "SEND_INTENT_RESULT_MISSING", requestId: null });
        setSendState("error");
        return;
      }
      setMockSend({
        outboundMessageId: res.result.outbound_message_id,
        status: res.result.status,
        sentAt: res.result.sent_at ?? null,
        mockOnly: Boolean(res.mock_only ?? res.result.mock_only),
      });
      setSendState("success");
    } catch (err) {
      setSafeError("send", err, "The local/mock send intent failed safely. No real email was sent.");
      setSendState("error");
    }
  }

  async function handleCreateFollowUpRule() {
    if (!canAct || !selectedTenantId || !mockSend || ruleState === "submitting") return;

    setRuleState("submitting");
    setFollowUpRule(null);
    setFollowUpSchedule(null);
    setMockRunSchedule(null);
    setError(null);

    try {
      const res = await createFollowUpRule(authOptions(selectedTenantId), {
        campaign_id: campaignIdForFollowUp(item),
        delay_seconds: 86400,
      });
      if (!res.followup_rule) {
        setError({ scope: "followup", message: "The backend mock API did not return a follow-up rule. No success was recorded.", code: "FOLLOWUP_RULE_MISSING", requestId: null });
        setRuleState("error");
        return;
      }
      setFollowUpRule({
        id: res.followup_rule.id,
        campaignId: res.followup_rule.campaign_id,
        delaySeconds: res.followup_rule.delay_seconds,
        mockOnly: Boolean(res.mock_only ?? res.followup_rule.mock_only),
      });
      setRuleState("success");
    } catch (err) {
      setSafeError("followup", err, "The local/mock follow-up rule create failed safely. No real email was sent.");
      setRuleState("error");
    }
  }

  async function handleCreateFollowUpSchedule() {
    if (!canAct || !selectedTenantId || !mockSend || !followUpRule || scheduleState === "submitting") return;

    setScheduleState("submitting");
    setFollowUpSchedule(null);
    setMockRunSchedule(null);
    setError(null);

    try {
      const res = await createFollowUpSchedule(authOptions(selectedTenantId), {
        original_outbound_message_id: mockSend.outboundMessageId,
      });
      if (!res.followup_schedule) {
        setError({ scope: "followup", message: "The backend mock API did not return a follow-up schedule. No success was recorded.", code: "FOLLOWUP_SCHEDULE_MISSING", requestId: null });
        setScheduleState("error");
        return;
      }
      setFollowUpSchedule({
        id: res.followup_schedule.id,
        status: res.followup_schedule.status,
        runAfter: res.followup_schedule.run_after,
        originalOutboundMessageId: res.followup_schedule.original_outbound_message_id,
        mockOnly: Boolean(res.mock_only ?? res.followup_schedule.mock_only),
      });
      setScheduleState("success");
    } catch (err) {
      setSafeError("followup", err, "The local/mock follow-up schedule create failed safely. No real email was sent.");
      setScheduleState("error");
    }
  }

  async function handleMockRunFollowUp() {
    if (!canAct || !selectedTenantId || !followUpSchedule || mockRunState === "submitting") return;

    setMockRunState("submitting");
    setMockRunSchedule(null);
    setError(null);

    try {
      const res = await mockRunFollowUpSchedule(authOptions(selectedTenantId), followUpSchedule.id);
      if (!res.followup_schedule) {
        setError({ scope: "followup", message: "The backend mock API did not return a mock-run follow-up schedule. No success was recorded.", code: "FOLLOWUP_MOCK_RUN_MISSING", requestId: null });
        setMockRunState("error");
        return;
      }
      setMockRunSchedule({
        id: res.followup_schedule.id,
        status: res.followup_schedule.status,
        runAfter: res.followup_schedule.run_after,
        originalOutboundMessageId: res.followup_schedule.original_outbound_message_id,
        mockOnly: Boolean(res.mock_only ?? res.followup_schedule.mock_only),
      });
      setMockRunState("success");
    } catch (err) {
      setSafeError("followup", err, "The local/mock follow-up mock-run failed safely. No real email was sent.");
      setMockRunState("error");
    }
  }

  return (
    <BentoCard title="Send gate and follow-up readiness" description="Send-gate, mock send intent, and local/mock follow-up actions call backend mock APIs only. No real email is sent and no SMTP, SendGrid, Mailgun, Gmail, webhook, DNS, or provider dispatch is called." badge="No real send">
      <div className="space-y-3">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <MailCheck className="size-4 text-yellow" /> Send readiness
            </div>
            <GateReasonBadge state={item.sendReadiness} label="Review context" className="mt-3" />
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <ShieldAlert className="size-4 text-blue" /> Send-gate dry-run
            </div>
            <GateReasonBadge state={gateAllowed ? "passed" : gate ? "blocked" : "pending"} label={gate ? gate.status : "Required first"} className="mt-3" />
          </div>
          <div className="rounded-medium border border-border bg-panel2 p-3">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <CalendarClock className="size-4 text-blue" /> Follow-up
            </div>
            <GateReasonBadge state={mockRunSchedule ? "passed" : followUpSchedule ? "pending" : "blocked"} label={mockRunSchedule ? "Mock-run done" : followUpSchedule ? "Mock scheduled" : "No real dispatch"} className="mt-3" />
          </div>
        </div>

        {gateState === "success" && gate ? (
          <div className="rounded-medium border border-border bg-panel2 p-4" role="status">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              {gateAllowed ? <CheckCircle2 className="size-4 text-green" /> : <AlertCircle className="size-4 text-yellow" />}
              Send-gate dry-run {gateAllowed ? "allowed" : "blocked"} by backend mock API
            </div>
            <p className="mt-2 text-small text-muted">
              Result ID: {gate.id}. Status: {gate.status}. Reason: {gate.denyReason ?? "none"}. Mock only: {gate.mockOnly ? "yes" : "not reported"}. No real email was sent.
            </p>
          </div>
        ) : null}

        {sendState === "success" && mockSend ? (
          <div className="rounded-medium border border-green/30 bg-greenbg/60 p-4" role="status">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <CheckCircle2 className="size-4 text-green" /> Backend mock send intent created
            </div>
            <p className="mt-2 text-small text-muted">
              Outbound message ID: {mockSend.outboundMessageId}. Status: {mockSend.status}. Sent at: {mockSend.sentAt ?? "not sent"}. Mock only: {mockSend.mockOnly ? "yes" : "not reported"}. No real email was sent.
            </p>
          </div>
        ) : null}

        {ruleState === "success" && followUpRule ? (
          <div className="rounded-medium border border-blue/30 bg-bluebg/50 p-4" role="status">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <CheckCircle2 className="size-4 text-green" /> Backend mock follow-up rule created
            </div>
            <p className="mt-2 text-small text-muted">
              Rule ID: {followUpRule.id}. Campaign ID: {followUpRule.campaignId}. Delay: {followUpRule.delaySeconds} seconds. Mock only: {followUpRule.mockOnly ? "yes" : "not reported"}. No real email was sent.
            </p>
          </div>
        ) : null}

        {scheduleState === "success" && followUpSchedule ? (
          <div className="rounded-medium border border-blue/30 bg-bluebg/50 p-4" role="status">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <CheckCircle2 className="size-4 text-green" /> Backend mock follow-up schedule created
            </div>
            <p className="mt-2 text-small text-muted">
              Schedule ID: {followUpSchedule.id}. Status: {followUpSchedule.status}. Run after: {followUpSchedule.runAfter}. Original outbound: {followUpSchedule.originalOutboundMessageId}. No real email was sent.
            </p>
          </div>
        ) : null}

        {mockRunState === "success" && mockRunSchedule ? (
          <div className="rounded-medium border border-green/30 bg-greenbg/60 p-4" role="status">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <CheckCircle2 className="size-4 text-green" /> Backend mock follow-up mock-run completed
            </div>
            <p className="mt-2 text-small text-muted">
              Schedule ID: {mockRunSchedule.id}. Status: {mockRunSchedule.status}. Mock only: {mockRunSchedule.mockOnly ? "yes" : "not reported"}. No real email was sent.
            </p>
          </div>
        ) : null}

        {error ? (
          <div className="rounded-medium border border-red/30 bg-redbg/60 p-4" role="alert">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <AlertCircle className="size-4 text-red" /> {error.scope === "followup" ? "Backend mock follow-up action failed safely" : "Backend mock send action failed safely"}
            </div>
            <p className="mt-2 text-small text-muted">{error.message}</p>
            <p className="mt-2 text-caption text-muted">
              Code: {error.code}{error.requestId ? ` · Request ID: ${error.requestId}` : ""}. No real email was sent and no fake success was recorded.
            </p>
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <Button onClick={handleDryRun} disabled={!canAct || gateState === "submitting"}>
            {gateState === "submitting" ? <Loader2 className="size-4 animate-spin" /> : <ShieldAlert className="size-4" />}
            {gateState === "submitting" ? "Running send-gate dry-run" : "Run send-gate dry-run"}
          </Button>
          <Button onClick={handleMockSendIntent} disabled={!canAct || !gateAllowed || sendState === "submitting"} variant="secondary">
            {sendState === "submitting" ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
            {sendState === "submitting" ? "Creating mock send intent" : "Create mock send intent"}
          </Button>
          <Button onClick={handleCreateFollowUpRule} disabled={!canAct || !mockSend || ruleState === "submitting" || followUpBusy} variant="secondary">
            {ruleState === "submitting" ? <Loader2 className="size-4 animate-spin" /> : <CalendarClock className="size-4" />}
            {ruleState === "submitting" ? "Creating follow-up rule" : "Create follow-up rule"}
          </Button>
          <Button onClick={handleCreateFollowUpSchedule} disabled={!canAct || !mockSend || !followUpRule || scheduleState === "submitting" || mockRunState === "submitting"} variant="secondary">
            {scheduleState === "submitting" ? <Loader2 className="size-4 animate-spin" /> : <CalendarClock className="size-4" />}
            {scheduleState === "submitting" ? "Creating follow-up schedule" : "Create follow-up schedule"}
          </Button>
          <Button onClick={handleMockRunFollowUp} disabled={!canAct || !followUpSchedule || mockRunState === "submitting"} variant="secondary">
            {mockRunState === "submitting" ? <Loader2 className="size-4 animate-spin" /> : <CalendarClock className="size-4" />}
            {mockRunState === "submitting" ? "Running follow-up mock-run" : "Run follow-up mock-run"}
          </Button>
          <Button disabled variant="locked">
            Real email sending disabled
          </Button>
        </div>
      </div>
    </BentoCard>
  );
}
