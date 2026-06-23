export interface ImportPreviewRow {
  id: string;
  fullName: string;
  company: string;
  title: string;
  domain: string;
  segment: string;
  validation: "valid" | "warning" | "blocked";
  note: string;
}

export const sampleCsvColumns = ["full_name", "company", "title", "domain", "segment"];

export const suggestedColumnMapping = [
  { source: "full_name", target: "name", status: "mapped" },
  { source: "company", target: "company", status: "mapped" },
  { source: "title", target: "role/title", status: "mapped" },
  { source: "domain", target: "email/domain", status: "mapped" },
  { source: "segment", target: "market/segment", status: "mapped" },
] as const;

export const importPreviewRows: ImportPreviewRow[] = [
  {
    id: "import_row_001",
    fullName: "Demo Contact 1",
    company: "Demo Properties A",
    title: "Acquisitions Lead",
    domain: "demo-a.example",
    segment: "CRE / Multifamily",
    validation: "valid",
    note: "Ready for local preview only.",
  },
  {
    id: "import_row_002",
    fullName: "Demo Contact 2",
    company: "Demo Assets B",
    title: "Managing Partner",
    domain: "demo-b.example",
    segment: "CRE / Industrial",
    validation: "warning",
    note: "Needs compliance review before outreach.",
  },
  {
    id: "import_row_003",
    fullName: "Demo Contact 3",
    company: "Demo Realty C",
    title: "Portfolio Director",
    domain: "demo-c.example",
    segment: "CRE / Retail",
    validation: "blocked",
    note: "Suppression/compliance block in demo data.",
  },
];
