import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { CsvImportWizard } from "@/components/import/csv-import-wizard";
import { PageHeader } from "@/components/layout/page-header";

import { Button } from "@/components/ui/button";

export default function ProspectImportPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="CSV import wizard"
        title="Import prospects"
        description="Import prospective contacts from a CSV list."
        actions={<Button asChild variant="secondary">
              <Link href="/prospects">
                <ArrowLeft className="size-4" /> Back to prospects
              </Link>
            </Button>}
      />

      <CsvImportWizard />
    </section>
  );
}
