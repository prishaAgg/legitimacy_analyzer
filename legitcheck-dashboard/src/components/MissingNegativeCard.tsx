import { AlertTriangle, XCircle, CheckCircle2 } from "lucide-react";

interface Props {
  missingSignals: string[];
  negativeSignals: string[];
}

const MissingNegativeCard = ({ missingSignals, negativeSignals }: Props) => {
  return (
    <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        Missing vs Negative Signals
      </h3>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-md border border-border bg-signal-neutral-bg p-4">
          <div className="mb-2 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-signal-neutral" />
            <span className="text-sm font-semibold text-signal-neutral">No Information Found</span>
          </div>
          {missingSignals.length === 0 ? (
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <CheckCircle2 className="h-3.5 w-3.5 text-signal-positive" />
              All signals accounted for
            </div>
          ) : (
            <ul className="space-y-1">
              {missingSignals.map((s, i) => (
                <li key={i} className="text-sm text-muted-foreground">• {s}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-md border border-border bg-signal-negative-bg p-4">
          <div className="mb-2 flex items-center gap-2">
            <XCircle className="h-4 w-4 text-signal-negative" />
            <span className="text-sm font-semibold text-signal-negative">Negative Signals Detected</span>
          </div>
          {negativeSignals.length === 0 ? (
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <CheckCircle2 className="h-3.5 w-3.5 text-signal-positive" />
              No negative signals detected
            </div>
          ) : (
            <ul className="space-y-1">
              {negativeSignals.map((s, i) => (
                <li key={i} className="text-sm text-muted-foreground">• {s}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};

export default MissingNegativeCard;
