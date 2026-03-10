import { DossierReport } from "@/types/dossier";

interface CredibilityScoreProps {
  score: number;
  verdict: DossierReport["verdict"];
}

const CredibilityScore = ({ score, verdict }: CredibilityScoreProps) => {
  const getVerdictStyle = () => {
    switch (verdict) {
      case "Likely Legitimate":
        return "text-signal-positive bg-signal-positive-bg";
      case "Uncertain":
        return "text-signal-neutral bg-signal-neutral-bg";
      case "Potential Risk":
        return "text-signal-negative bg-signal-negative-bg";
    }
  };

  const getScoreColor = () => {
    if (score >= 7) return "text-signal-positive";
    if (score >= 5) return "text-signal-neutral";
    return "text-signal-negative";
  };

  return (
    <div className="flex items-center gap-6">
      <div className="text-center">
        <span className={`text-5xl font-bold tabular-nums ${getScoreColor()}`}>
          {score.toFixed(1)}
        </span>
        <span className="text-lg text-muted-foreground"> / 10</span>
      </div>
      <span className={`rounded-full px-4 py-1.5 text-sm font-semibold ${getVerdictStyle()}`}>
        {verdict}
      </span>
    </div>
  );
};

export default CredibilityScore;
