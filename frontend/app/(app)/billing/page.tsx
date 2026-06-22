import { BillingBanner, readOnlyBillingStatus } from "@/components/billing-banner";

export default function BillingPage() {
  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Billing</h1>
        <p className="mt-2 text-sm text-slate-600">
          Mock MVP billing is shown as a safe read-only contract until backend tenant access is confirmed.
        </p>
      </div>
      <BillingBanner status={readOnlyBillingStatus} />
      <div className="rounded-lg border bg-white p-4 text-sm text-slate-700">
        <p className="font-medium text-slate-900">Payment actions disabled</p>
        <p className="mt-1">No checkout, payment method, or provider billing UI exists in Phase 0.</p>
      </div>
    </section>
  );
}
