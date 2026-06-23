import { DraftGatePanel } from "./draft-gate-panel";
import { DraftPreview } from "./draft-preview";
import { GroundednessPanel } from "./groundedness-panel";
import type { DraftRow } from "./draft-sample-data";

export function DraftDetailDrawer({ draft }: { draft: DraftRow }) {
  return (
    <div className="space-y-4">
      <DraftPreview draft={draft} />
      <GroundednessPanel draft={draft} />
      <DraftGatePanel draft={draft} />
    </div>
  );
}
