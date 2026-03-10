import { DossierReport } from "@/types/dossier";
import { format } from "date-fns";

interface Props {
  reports: DossierReport[];
  onSelect: (report: DossierReport) => void;
}

const verdictStyle = (verdict: DossierReport["verdict"]) => {
  switch (verdict) {
    case "Likely Legitimate":
      return "text-signal-positive bg-signal-positive-bg";
    case "Uncertain":
      return "text-signal-neutral bg-signal-neutral-bg";
    case "Potential Risk":
      return "text-signal-negative bg-signal-negative-bg";
  }
};

const scoreColor = (score: number) => {
  if (score >= 7) return "text-signal-positive";
  if (score >= 5) return "text-signal-neutral";
  return "text-signal-negative";
};

const PastReportsTable = ({ reports, onSelect }: Props) => {
  if (reports.length === 0) {
    return (
      <div className="mt-8 text-center text-muted-foreground">
        No past reports yet. Generate your first report to get started.
      </div>
    );
  }

  return (
    <div className="mt-4 overflow-hidden rounded-lg border border-border bg-card shadow-sm">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Date</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Business Name</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Location</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Score</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">Verdict</th>
          </tr>
        </thead>
        <tbody>
          {reports.map((report) => (
            <tr
              key={report.id}
              onClick={() => onSelect(report)}
              className="cursor-pointer border-b border-border transition-colors last:border-0 hover:bg-muted/50"
            >
              <td className="px-4 py-3 text-muted-foreground">
                {format(new Date(report.timestamp), "MMM d, yyyy")}
              </td>
              <td className="px-4 py-3 font-medium text-card-foreground">{report.businessName}</td>
              <td className="px-4 py-3 text-muted-foreground">{report.location}</td>
              <td className={`px-4 py-3 font-semibold tabular-nums ${scoreColor(report.credibilityScore)}`}>
                {report.credibilityScore.toFixed(1)}
              </td>
              <td className="px-4 py-3">
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${verdictStyle(report.verdict)}`}>
                  {report.verdict}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default PastReportsTable;
