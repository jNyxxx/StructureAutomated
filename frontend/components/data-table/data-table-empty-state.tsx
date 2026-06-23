import { EmptyState } from "@/components/states";

export function DataTableEmptyState({ title = "No rows found", description = "Try changing filters or search terms." }: { title?: string; description?: string }) {
  return <EmptyState title={title} description={description} />;
}
