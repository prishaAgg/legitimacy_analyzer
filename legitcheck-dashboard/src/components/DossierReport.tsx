import { DossierReport as DossierReportType } from "@/types/dossier";
import CredibilityScore from "./CredibilityScore";
import SignalCard from "./SignalCard";
import MissingNegativeCard from "./MissingNegativeCard";
import { CheckCircle2, MapPin, Clock, FileText, AlertCircle, TrendingUp } from "lucide-react";
import { format } from "date-fns";

const DossierReport = ({ report }: { report: DossierReportType }) => {
  const formattedDate = format(new Date(report.timestamp), "MMM d, yyyy 'at' h:mm a");

  return (
    <div className="mt-6 space-y-5">

      {/* Spelling / disambiguation warning */}
      {report.nameFlag && (
        <div className="flex items-start gap-2 rounded-lg border border-yellow-300 bg-yellow-50 p-4 text-sm text-yellow-800">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{report.nameFlag}</span>
        </div>
      )}

      {/* Business Summary */}
      <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-2xl font-bold text-card-foreground">{report.businessName}</h2>
              {report.ticker && (
                <a
                  href={report.ticker.url || "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 rounded-md border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-100 transition-colors"
                  title={`Listed on ${report.ticker.exchange}`}
                >
                  <TrendingUp className="h-3 w-3" />
                  {report.ticker.symbol}
                  <span className="font-normal opacity-70">{report.ticker.exchange}</span>
                </a>
              )}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5" /> {report.location}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" /> {formattedDate}
              </span>
            </div>
          </div>
          <CredibilityScore score={report.credibilityScore} verdict={report.verdict} />
        </div>
        <div className="rounded-md bg-card p-4">
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Key Findings
          </h4>
          <ul className="space-y-1">
            {report.reasoning.map((r, i) => (
              <li key={i} className="flex min-w-0 items-start gap-2 text-sm text-card-foreground">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-signal-positive" />
                <span className="break-words min-w-0">{r}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Signal Breakdown */}
      <div>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Signal Breakdown
        </h3>
        <div className="grid gap-4 md:grid-cols-2">
          {report.signals.map((signal, i) => (
            <SignalCard key={i} signal={signal} />
          ))}
        </div>
      </div>

      {/* Missing vs Negative */}
      <MissingNegativeCard
        missingSignals={report.missingSignals}
        negativeSignals={report.negativeSignals}
      />

      {/* Sources */}
      {report.sources.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            <FileText className="h-4 w-4" /> All Sources
          </h3>
          <ul className="space-y-1">
            {report.sources.map((s, i) => (
              <li key={i} className="text-sm text-muted-foreground">
                •{" "}
                {/^https?:\/\//.test(s.trim()) ? (
                  <a href={s.trim()} target="_blank" rel="noopener noreferrer"
                    className="underline hover:text-primary break-all">
                    {s.trim()}
                  </a>
                ) : s}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default DossierReport;