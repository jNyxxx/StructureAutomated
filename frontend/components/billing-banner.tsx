import type { BillingGateStatus } from "@/lib/schemas";

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
  normal: "border-emerald-200 bg-emerald-50 text-emerald-900",
  limited: "border-amber-200 bg-amber-50 text-amber-900",
  read_only: "border-slate-200 bg-slate-50 text-slate-700",
  locked: "border-red-200 bg-red-50 text-red-900",
  loading: "border-slate-200 bg-slate-50 text-slate-700",
  error: "border-red-200 bg-red-50 text-red-900",
};

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
