import { BillingLockedState } from "@/components/states";
import { PageHeader } from "@/components/layout/page-header";
import { BillingBanner, readOnlyBillingStatus } from "@/components/billing-banner";

export default function BillingPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Access gates"
        title="Billing"
        description="Mock MVP billing is shown as a safe read-only contract until backend tenant access is confirmed."
      />
      <BillingBanner status={readOnlyBillingStatus} />
      <BillingLockedState
        state="inactive"
        title="Payment actions disabled"
        description="No real Stripe checkout, payment method, provider billing, dunning, or money movement exists in this frontend slice. Billing-dependent actions remain read-only/locked."
      />
    </section>
  );
}
