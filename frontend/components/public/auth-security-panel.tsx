import { KeyRound, ShieldAlert, ScrollText, ShieldCheck } from "lucide-react";

const items = [
  { icon: ShieldCheck, text: "Enterprise tenant isolation" },
  { icon: KeyRound, text: "Multi-factor authentication ready" },
  { icon: ScrollText, text: "Cryptographic activity auditing" },
  { icon: ShieldAlert, text: "AI prompt injection protection" },
];

export function AuthSecurityPanel() {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <div key={item.text} className="flex items-center gap-3 rounded-medium border border-border bg-panel/80 p-3 text-small text-muted">
            <Icon className="size-4 text-blue" />
            <span>{item.text}</span>
          </div>
        );
      })}
    </div>
  );
}
