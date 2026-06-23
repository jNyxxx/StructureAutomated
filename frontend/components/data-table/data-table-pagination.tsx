import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";

export function DataTablePagination({
  page,
  pageCount,
  pageSize,
  totalRows,
  onPageChange,
}: {
  page: number;
  pageCount: number;
  pageSize: number;
  totalRows: number;
  onPageChange: (page: number) => void;
}) {
  const safePageCount = Math.max(pageCount, 1);
  const start = totalRows === 0 ? 0 : page * pageSize + 1;
  const end = Math.min((page + 1) * pageSize, totalRows);

  return (
    <div className="flex flex-col gap-3 border-t border-border px-4 py-3 text-small text-muted sm:flex-row sm:items-center sm:justify-between">
      <p>
        Showing {start}–{end} of {totalRows} rows
      </p>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(Math.max(page - 1, 0))}
          disabled={page <= 0}
          aria-label="Previous page"
        >
          <ChevronLeft className="size-4" />
          Previous
        </Button>
        <span className="rounded-medium border border-border bg-panel2 px-3 py-2 text-caption">
          Page {page + 1} of {safePageCount}
        </span>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => onPageChange(Math.min(page + 1, safePageCount - 1))}
          disabled={page >= safePageCount - 1}
          aria-label="Next page"
        >
          Next
          <ChevronRight className="size-4" />
        </Button>
      </div>
    </div>
  );
}
