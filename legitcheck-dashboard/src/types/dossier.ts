export type SignalStatus = "positive" | "neutral" | "negative";

export interface SignalFinding {
  label: string;
  value: string;
  status: SignalStatus;
}

export interface Signal {
  title: string;
  status: SignalStatus;
  findings: SignalFinding[];
  interpretation: string;
  source: string;
  sources?: string[];   // ← clickable URLs for this signal
}

export interface DossierReport {
  id: string;
  businessName: string;
  location: string;
  timestamp: string;
  credibilityScore: number;
  verdict: "Likely Legitimate" | "Uncertain" | "Potential Risk";
  reasoning: string[];
  signals: Signal[];
  missingSignals: string[];
  negativeSignals: string[];
  sources: string[];
  nameFlag?: string | null;
  ticker?: { symbol: string; exchange: string; url?: string } | null;
}