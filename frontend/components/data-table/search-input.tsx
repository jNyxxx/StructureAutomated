import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";

export function SearchInput({
  value,
  onChange,
  placeholder = "Search rows...",
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="relative min-w-0 flex-1 sm:max-w-sm">
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-subtle" />
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-pill bg-panel2 pl-9"
        placeholder={placeholder}
        aria-label={placeholder}
      />
    </div>
  );
}
