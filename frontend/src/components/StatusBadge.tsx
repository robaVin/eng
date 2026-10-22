const STYLES: Record<string, string> = {
  uploaded: "bg-slate-100 text-slate-600",
  analyzing: "bg-blue-100 text-blue-700",
  analyzed: "bg-amber-100 text-amber-700",
  approved: "bg-green-100 text-green-700",
  error: "bg-red-100 text-red-700",
};

const LABELS: Record<string, string> = {
  uploaded: "Uploaded",
  analyzing: "Analyzing",
  analyzed: "Needs review",
  approved: "Approved",
  error: "Error",
};

export default function StatusBadge({ status }: { status: string }) {
  return <span className={`badge ${STYLES[status] ?? "bg-slate-100 text-slate-600"}`}>{LABELS[status] ?? status}</span>;
}
