/**
 * src/lib/api.ts
 * ==============
 * The ONLY file in the dashboard that talks to the backend.
 *
 * Architecture: submit → poll → done
 *   1. POST /api/runs/        → creates a job, returns { id } immediately
 *   2. GET  /api/runs/{id}    → poll every 2s until status === "complete"
 *   3. GET  /api/analyze-business/{id} → fetch the formatted DossierReport
 *
 * This means the frontend never blocks on a 20s HTTP request.
 * The backend processes in the background; we just check in periodically.
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const POLL_INTERVAL_MS = 2000;   // check every 2 seconds
const POLL_TIMEOUT_MS  = 120000; // give up after 2 minutes

// ── Main entry point ──────────────────────────────────────────────────────────

/**
 * Submit a business for analysis, poll until complete, return the DossierReport.
 * Replaces the old single blocking fetchReport() call.
 */
export async function fetchReport(
  businessName: string,
  location: string,
  forceRefresh = false,
): Promise<DossierReport> {
  // 1. Submit the job — returns immediately with a run ID
  const run = await _submitJob(businessName, location, forceRefresh);

  // 2. Poll until done
  const completedRun = await _pollUntilComplete(run.id);

  // 3. Fetch the formatted DossierReport
  return _fetchDossier(completedRun.id);
}

/**
 * Fetch the last N completed reports, newest first.
 * Populates the Past Reports tab on page load.
 */
export async function fetchHistory(limit = 20): Promise<DossierReport[]> {
  const res = await fetch(`${BASE_URL}/api/analyze-business/history?limit=${limit}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Internal helpers ──────────────────────────────────────────────────────────

async function _submitJob(
  businessName: string,
  location: string,
  forceRefresh: boolean,
): Promise<{ id: number; status: string }> {
  const res = await fetch(`${BASE_URL}/api/runs/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      business_name: businessName,
      location,
      force_refresh: forceRefresh,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `Failed to submit job: HTTP ${res.status}`);
  }
  return res.json();
}

async function _pollUntilComplete(runId: number): Promise<{ id: number; status: string }> {
  const deadline = Date.now() + POLL_TIMEOUT_MS;

  while (Date.now() < deadline) {
    await _sleep(POLL_INTERVAL_MS);

    const res = await fetch(`${BASE_URL}/api/runs/${runId}`);
    if (!res.ok) throw new Error(`Polling failed: HTTP ${res.status}`);

    const run = await res.json();

    if (run.status === "complete") return run;
    if (run.status === "error") {
      throw new Error(run.error_message ?? "Analysis failed on the backend.");
    }
    // status === "running" → keep polling
  }

  throw new Error("Analysis timed out after 2 minutes.");
}

async function _fetchDossier(runId: number): Promise<DossierReport> {
  const res = await fetch(`${BASE_URL}/api/analyze-business/${runId}`);
  if (!res.ok) throw new Error(`Failed to fetch report: HTTP ${res.status}`);
  return res.json();
}

function _sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Types (source of truth is src/types/dossier.ts- keep in sync) 

type SignalStatus = "positive" | "neutral" | "negative";

interface DossierReport {
  id: string;
  businessName: string;
  location: string;
  timestamp: string;
  credibilityScore: number;
  verdict: "Likely Legitimate" | "Uncertain" | "Potential Risk";
  reasoning: string[];
  signals: {
    title: string;
    status: SignalStatus;
    findings: { label: string; value: string; status: SignalStatus }[];
    interpretation: string;
    source: string;
    sources?: string[];
  }[];
  missingSignals: string[];
  negativeSignals: string[];
  sources: string[];
  nameFlag?: string | null;
  ticker?: { symbol: string; exchange: string; url?: string } | null;
}