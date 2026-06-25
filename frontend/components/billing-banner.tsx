import type { BillingGateStatus, BillingAccess, BillingSubscription } from "@/lib/schemas";

export const readOnlyBillingStatus: BillingGateStatus = {
  tenant_id: null,
  tenant_status: "unknown",
  mode: "read_only",
  is_active: false,
  gates: {
    can_send: false,
    can_run_agents: false,
    can_create_campaign: false,
    can_export: false,
  },
  message: "Billing status is not confirmed by the backend yet. Costly/outbound actions stay locked.",
};

const modeClass: Record<BillingGateStatus["mode"], string> = {
  normal: "border-green/20 bg-goodbg/60 text-green",
  limited: "border-yellow/20 bg-warnbg/60 text-yellow",
  read_only: "border-border bg-panel2/60 text-muted",
  locked: "border-red/20 bg-redbg/60 text-red",
  loading: "border-border bg-panel2/60 text-muted",
  error: "border-red/20 bg-redbg/60 text-red",
};

export function deriveBillingGateStatus(
  access: BillingAccess | null,
  subscription: BillingSubscription | null,
  tenantId: string | null
): BillingGateStatus {
  if (!access || !subscription) {
    return {
      ...readOnlyBillingStatus,
      tenant_id: tenantId,
    };
  }

  let mode: BillingGateStatus["mode"] = "read_only";
  let message = "Billing status is loaded. Some features might be restricted.";

  const status = subscription.tenant_status;

  if (status === "active" || status === "trialing") {
    mode = "normal";
    message = `Subscription is ${status}. All gated features are active.`;
  } else if (status === "past_due") {
    mode = "limited";
    message = "Subscription payment is past due. Access continues during grace period.";
  } else if (status === "canceled" || status === "unpaid" || status === "inactive") {
    mode = "locked";
    message = `Subscription is ${status}. Gated features, campaign creation, and sending are locked.`;
  }

  return {
    tenant_id: tenantId,
    tenant_status: status as any,
    mode,
    is_active: access.is_active,
    gates: {
      can_send: access.can_send,
      can_run_agents: access.can_run_agents,
      can_create_campaign: access.can_create_campaign,
      can_export: access.can_export,
    },
    message,
  };
}

export function BillingBanner({ status = readOnlyBillingStatus }: { status?: BillingGateStatus }) {
  return (
    <aside className={`rounded-lg border p-4 text-sm ${modeClass[status.mode]}`}>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-medium">Billing: {status.tenant_status}</p>
          <p className="mt-1">{status.message}</p>
        </div>
        <span className="rounded-full border px-3 py-1 text-xs font-medium uppercase tracking-wide">
          {status.mode.replace("_", " ")}
        </span>
      </div>
      <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-4">
        <GateLabel label="Send" value={status.gates.can_send} />
        <GateLabel label="Agents" value={status.gates.can_run_agents} />
        <GateLabel label="Campaigns" value={status.gates.can_create_campaign} />
        <GateLabel label="Exports" value={status.gates.can_export} />
      </dl>
    </aside>
  );
}

function GateLabel({ label, value }: { label: string; value: boolean }) {
  return (
    <div className="rounded border border-current/20 px-2 py-1">
      <dt className="font-medium">{label}</dt>
      <dd>{value ? "Allowed" : "Locked"}</dd>
    </div>
  );
}
