import { AlertCircle } from "lucide-react";

import { cn } from "@/lib/utils";

export interface ValidationErrorItem {
  field?: string;
  message: string;
  code?: string;
}

export function ValidationErrorList({
  errors,
  title = "Validation errors",
  className,
}: {
  errors: ValidationErrorItem[];
  title?: string;
  className?: string;
}) {
  if (errors.length === 0) return null;

  return (
    <div className={cn("rounded-medium border border-red/30 bg-redbg p-4 text-small text-red", className)}>
      <div className="flex items-center gap-2 font-semibold">
        <AlertCircle className="size-4" />
        {title}
      </div>
      <ul className="mt-3 space-y-2 text-muted">
        {errors.map((error, index) => (
          <li key={`${error.field ?? "global"}-${error.code ?? index}`} className="flex gap-2">
            <span className="text-red">•</span>
            <span>
              {error.field ? <strong className="text-text">{error.field}: </strong> : null}
              {error.message}
              {error.code ? <span className="text-subtle"> ({error.code})</span> : null}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
