"use client";

import { useState } from "react";
import { AlertCircle, CalendarClock, CheckCircle2, Loader2, MailCheck, Send, ShieldAlert } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { BentoCard } from "@/components/dashboard/bento-card";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { createSendIntent, runSendGateDryRun } from "@/lib/backend-api";
import { useFrontendAuth } from "@/lib/clerk";
import { useTenantContext } from "@/lib/tenant-context";
import type { ReviewItem } from "./review-sample-data";

type ActionState = "idle" | "submitting" | "success" | "error";

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

function isGateAllowed(status: string): boolean {
  return ["allowed", "passed", "approved", "ready"].includes(status.toLowerCase());
}

export function SendReadinessPanel({ item }: { item: ReviewItem }) {
  const auth = useFrontendAuth();
  const { selectedTenantId } = useTenantContext();
  const [gateState, setGateState] = useState<ActionState>("idle");
  const [sendState, setSendState] = useState<ActionState>("idle");
  const [gate, setGate] = useState<GateSummary | null>(null);
  const [mockSend, setMockSend] = useState<MockSendSummary | null>(null);
  const [error, setError] = useState<{ message: string; code: string; requestId: string | null } | null>(null);
  const canAct = auth.isLoaded && auth.isSignedIn && Boolean(selectedTenantId);
  const gateAllowed = gate ? isGateAllowed(gate.status) : false;

  async function handleDryRun() {
    if (!canAct || !selectedTenantId || gateState === "submitting") return;

    setGateState("submitting");
    setSendState("idle");
    setGate(null);
    setMockSend(null);
    setError(null);

    try {
      const res = await runSendGateDryRun(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        { draft_id: item.draft.id },
      );
      if (!res.send_gate_result) {
        setError({ message: "The backend mock API did not return a send-gate result. No success was recorded.", code: "SEND_GATE_RESULT_MISSING", requestId: null });
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
      if (err instanceof ApiError) {
        setError({ message: err.message, code: err.code, requestId: err.requestId });
      } else {
        setError({ message: "The local/mock send-gate dry-run failed safely. No send intent was created.", code: "UNKNOWN", requestId: null });
      }
      setGateState("error");
    }
  }

  async function handleMockSendIntent() {
    if (!canAct || !selectedTenantId || !gateAllowed || sendState === "submitting") return;

    setSendState("submitting");
    setMockSend(null);
    setError(null);

    try {
      const res = await createSendIntent(
        {
          getToken: auth.getToken,
          getTenantId: () => selectedTenantId,
        },
        { draft_id: item.draft.id },
      );
      if (!res.result) {
        setError({ message: "The backend mock API did not return a mock send intent result. No success was recorded.", code: "SEND_INTENT_RESULT_MISSING", requestId: null });
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
      if (err instanceof ApiError) {
        setError({ message: err.message, code: err.code, requestId: err.requestId });
      } else {
        setError({ message: "The local/mock send intent failed safely. No real email was sent.", code: "UNKNOWN", requestId: null });
      }
      setSendState("error");
    }
  }

  return (
    <BentoCard title="Send gate readiness" description="Send-gate dry-run and mock send intent call backend mock APIs only. No real email is sent and no SMTP, SendGrid, Mailgun, Gmail, webhook, DNS, or provider dispatch is called." badge="No real send">
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
            <GateReasonBadge state="blocked" label="Schedule locked" className="mt-3" />
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

        {error ? (
          <div className="rounded-medium border border-red/30 bg-redbg/60 p-4" role="alert">
            <div className="flex items-center gap-2 text-small font-semibold text-text">
              <AlertCircle className="size-4 text-red" /> Backend mock send action failed safely
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
          <Button disabled variant="secondary">
            <CalendarClock className="size-4" /> Schedule follow-up locked
          </Button>
          <Button disabled variant="locked">
            Real email sending disabled
          </Button>
        </div>
      </div>
    </BentoCard>
  );
}
