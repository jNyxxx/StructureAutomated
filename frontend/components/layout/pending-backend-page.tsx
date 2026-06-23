import { Lock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function PendingBackendPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-h2 text-text">{title}</h1>
          <p className="mt-2 max-w-2xl text-small text-muted">{description}</p>
        </div>
        <Badge variant="locked">Pending backend wiring</Badge>
      </div>
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-medium bg-panel2 text-muted">
              <Lock className="size-5" />
            </div>
            <div>
              <CardTitle>Local/mock MVP shell only</CardTitle>
              <CardDescription>
                This route is visible for navigation and design validation. Actions stay locked until the matching HTTP API is mounted.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-small text-muted">
            No production readiness, live sending, live scraping, Stripe billing, SMS, or webhook behavior is implemented here.
          </p>
        </CardContent>
      </Card>
    </section>
  );
}
