import type { BadgeProps } from "@/components/ui/badge";

type Tone = NonNullable<BadgeProps["variant"]>;

export type StatusToneKey =
  | "active"
  | "approved"
  | "complete"
  | "success"
  | "trialing"
  | "pending"
  | "queued"
  | "running"
  | "warning"
  | "past_due"
  | "failed"
  | "rejected"
  | "blocked"
  | "danger"
  | "locked"
  | "inactive"
  | "unknown";

export const statusToneMap: Record<StatusToneKey, Tone> = {
  active: "success",
  approved: "success",
  complete: "success",
  success: "success",
  trialing: "default",
  pending: "warning",
  queued: "warning",
  running: "violet",
  warning: "warning",
  past_due: "warning",
  failed: "danger",
  rejected: "danger",
  blocked: "danger",
  danger: "danger",
  locked: "locked",
  inactive: "locked",
  unknown: "outline",
};

export type GateReasonToneKey =
  | "billing"
  | "quota"
  | "permission"
  | "suppression"
  | "groundedness"
  | "prompt_injection"
  | "deliverability"
  | "throttle"
  | "duplicate"
  | "locked"
  | "unknown";

export const gateReasonToneMap: Record<GateReasonToneKey, Tone> = {
  billing: "warning",
  quota: "warning",
  permission: "danger",
  suppression: "danger",
  groundedness: "warning",
  prompt_injection: "danger",
  deliverability: "warning",
  throttle: "warning",
  duplicate: "locked",
  locked: "locked",
  unknown: "outline",
};

export type BillingStateToneKey =
  | "trialing"
  | "active"
  | "past_due"
  | "canceled"
  | "unpaid"
  | "inactive"
  | "unknown";

export const billingStateToneMap: Record<BillingStateToneKey, Tone> = {
  trialing: "default",
  active: "success",
  past_due: "warning",
  canceled: "locked",
  unpaid: "danger",
  inactive: "locked",
  unknown: "outline",
};

export function getStatusTone(status: string | null | undefined): Tone {
  const key = normalizeToneKey(status) as StatusToneKey;
  return statusToneMap[key] ?? statusToneMap.unknown;
}

export function getGateReasonTone(reason: string | null | undefined): Tone {
  const key = normalizeToneKey(reason) as GateReasonToneKey;
  return gateReasonToneMap[key] ?? gateReasonToneMap.unknown;
}

export function getBillingStateTone(state: string | null | undefined): Tone {
  const key = normalizeToneKey(state) as BillingStateToneKey;
  return billingStateToneMap[key] ?? billingStateToneMap.unknown;
}

function normalizeToneKey(value: string | null | undefined): string {
  return value?.trim().toLowerCase().replaceAll("-", "_") || "unknown";
}
