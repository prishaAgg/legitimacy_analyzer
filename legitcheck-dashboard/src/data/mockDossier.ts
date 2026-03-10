import { DossierReport } from "@/types/dossier";

export const generateMockReport = (businessName: string, location: string): DossierReport => {
  const id = crypto.randomUUID();
  const now = new Date().toISOString();

  return {
    id,
    businessName,
    location: location || "Not specified",
    timestamp: now,
    credibilityScore: 7.8,
    verdict: "Likely Legitimate",
    reasoning: [
      "Established domain (registered 2016)",
      "Strong customer reviews (4.2 rating across 200 reviews)",
      "Active social presence on LinkedIn and Instagram",
      "No adverse media detected",
    ],
    signals: [
      {
        title: "Website Credibility",
        status: "positive",
        findings: [
          { label: "Domain Age", value: "8 years (registered 2016)", status: "positive" },
          { label: "HTTPS", value: "Enabled", status: "positive" },
          { label: "Contact Info", value: "Phone, email, and address detected", status: "positive" },
        ],
        interpretation: "Website shows strong indicators of a legitimate, established business.",
        source: "WHOIS + website scan",
      },
      {
        title: "Customer Reviews",
        status: "positive",
        findings: [
          { label: "Average Rating", value: "4.2 / 5.0", status: "positive" },
          { label: "Total Reviews", value: "200", status: "positive" },
          { label: "Recent Reviews", value: "15 in last 30 days", status: "positive" },
        ],
        interpretation: "Consistent positive reviews with recent activity suggest genuine customer engagement.",
        source: "Yelp API",
      },
      {
        title: "Adverse Media Check",
        status: "positive",
        findings: [
          { label: "News Articles Found", value: "3", status: "neutral" },
          { label: "Negative Mentions", value: "0 (fraud, lawsuits, regulatory actions)", status: "positive" },
        ],
        interpretation: "No adverse media signals detected. Business appears clean in public records.",
        source: "News API",
      },
      {
        title: "Social Presence",
        status: "neutral",
        findings: [
          { label: "LinkedIn", value: "Found — 1,200 followers", status: "positive" },
          { label: "Instagram", value: "Found — 850 followers", status: "positive" },
          { label: "Twitter/X", value: "Not found", status: "neutral" },
          { label: "Recent Activity", value: "Last post 5 days ago", status: "positive" },
        ],
        interpretation: "Active presence on major platforms. Missing Twitter/X is a minor gap.",
        source: "Public social profiles",
      },
    ],
    missingSignals: ["Twitter/X profile not found", "No BBB listing detected"],
    negativeSignals: [],
    sources: [
      "WHOIS lookup",
      "Yelp Fusion API",
      "News API",
      "Public social profiles",
    ],
  };
};

export const mockPastReports: DossierReport[] = [
  {
    ...generateMockReport("Acme Corp", "New York, NY"),
    id: "1",
    timestamp: "2026-03-05T14:30:00Z",
    credibilityScore: 7.8,
    verdict: "Likely Legitimate",
  },
  {
    ...generateMockReport("TechStart LLC", "San Francisco, CA"),
    id: "2",
    timestamp: "2026-03-04T10:15:00Z",
    credibilityScore: 5.2,
    verdict: "Uncertain",
    businessName: "TechStart LLC",
    location: "San Francisco, CA",
    negativeSignals: ["Domain registered 3 months ago"],
    missingSignals: ["No reviews found", "No social media presence"],
  },
  {
    ...generateMockReport("QuickLoans Inc", "Miami, FL"),
    id: "3",
    timestamp: "2026-03-03T09:00:00Z",
    credibilityScore: 3.1,
    verdict: "Potential Risk",
    businessName: "QuickLoans Inc",
    location: "Miami, FL",
    negativeSignals: ["Multiple fraud complaints", "Regulatory warning issued"],
  },
  {
    ...generateMockReport("GreenLeaf Organic", "Portland, OR"),
    id: "4",
    timestamp: "2026-03-02T16:45:00Z",
    credibilityScore: 8.5,
    verdict: "Likely Legitimate",
    businessName: "GreenLeaf Organic",
    location: "Portland, OR",
  },
  {
    ...generateMockReport("DataBridge Solutions", "Austin, TX"),
    id: "5",
    timestamp: "2026-03-01T11:20:00Z",
    credibilityScore: 6.4,
    verdict: "Uncertain",
    businessName: "DataBridge Solutions",
    location: "Austin, TX",
    missingSignals: ["No BBB listing", "Limited review history"],
  },
];
