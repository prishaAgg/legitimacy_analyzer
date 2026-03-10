import { Signal, SignalStatus } from "@/types/dossier";
import { CheckCircle2, AlertTriangle, XCircle, ExternalLink } from "lucide-react";

const isUrl = (s: string) => /^https?:\/\//.test(s.trim());

const MaybeLink = ({ value }: { value: string }) => {
  if (isUrl(value)) {
    return (
      <a href={value.trim()} target="_blank" rel="noopener noreferrer"
        className="inline-flex items-center gap-1 underline hover:text-primary break-all">
        {value.trim()} <ExternalLink className="h-3 w-3 shrink-0" />
      </a>
    );
  }
  return <>{value}</>;
};

const statusConfig: Record<SignalStatus, { icon: typeof CheckCircle2; color: string; bg: string }> = {
  positive: { icon: CheckCircle2, color: "text-signal-positive", bg: "bg-signal-positive-bg" },
  neutral:  { icon: AlertTriangle, color: "text-signal-neutral",  bg: "bg-signal-neutral-bg"  },
  negative: { icon: XCircle,       color: "text-signal-negative", bg: "bg-signal-negative-bg" },
};

const SignalCard = ({ signal }: { signal: Signal }) => {
  const config = statusConfig[signal.status];
  const Icon   = config.icon;

  // Deduplicate sources that are already shown as finding values
  const findingUrls = new Set(
    signal.findings.filter(f => isUrl(f.value)).map(f => f.value.trim())
  );
  const extraSources = (signal.sources || []).filter(
    s => s && isUrl(s) && !findingUrls.has(s.trim())
  );

  return (
    <div className={`rounded-lg border border-border p-5 shadow-sm ${config.bg}`}>
      {/* Header */}
      <div className="mb-3 flex items-center gap-2">
        <div className={`rounded-full p-1 ${config.bg}`}>
          <Icon className={`h-4 w-4 ${config.color}`} />
        </div>
        <h3 className="font-semibold text-card-foreground">{signal.title}</h3>
      </div>

      {/* Findings */}
      <div className="mb-3 space-y-1.5">
        {signal.findings.map((f, i) => {
          const fConfig = statusConfig[f.status];
          const FIcon   = fConfig.icon;
          return (
            <div key={i} className="flex min-w-0 items-start gap-2 text-sm">
              <FIcon className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${fConfig.color}`} />
              <span className="break-words min-w-0 text-muted-foreground">
                <span className="font-medium text-card-foreground">{f.label}:</span>{" "}
                <MaybeLink value={f.value} />
              </span>
            </div>
          );
        })}
      </div>

      {/* Interpretation */}
      <p className="mb-2 text-sm italic text-muted-foreground">{signal.interpretation}</p>

      {/* Source label */}
      <p className="text-xs text-muted-foreground">
        Source: <span className="font-medium">{signal.source}</span>
      </p>

      {/* Extra source links not already shown in findings */}
      {extraSources.length > 0 && (
        <div className="mt-2 space-y-0.5">
          {extraSources.map((s, i) => (
            <a key={i} href={s} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-muted-foreground underline hover:text-primary break-all">
              <ExternalLink className="h-3 w-3 shrink-0" /> {s}
            </a>
          ))}
        </div>
      )}
    </div>
  );
};

export default SignalCard;