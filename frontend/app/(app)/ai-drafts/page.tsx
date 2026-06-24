import { AlertTriangle, Sparkles } from "lucide-react";

import { GateReasonBadge } from "@/components/badges";
import { DraftsTable } from "@/components/drafts/drafts-table";
import { ResearchWorkbench } from "@/components/research/research-workbench";
import { PageHeader } from "@/components/layout/page-header";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function AiDraftsPage() {
  return (
    <section className="space-y-6">
      <PageHeader
        eyebrow="Research/RAG and draft review"
        title="AI drafts"
        description="Review, optimize, and manage AI-generated outreach drafts."
        actions={<Button disabled>
              <Sparkles className="size-4" /> Generate locked
            </Button>}
      />

      <DraftsTable />
      <ResearchWorkbench />
    </section>
  );
}
