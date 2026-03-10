import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import SearchPanel from "@/components/SearchPanel";
import DossierReportView from "@/components/DossierReport";
import PastReportsTable from "@/components/PastReportsTable";
import { DossierReport } from "@/types/dossier";
import { Shield, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fetchReport, fetchHistory } from "@/lib/api";

// Loading messages shown while polling — gives the user a sense of progress
const LOADING_STEPS = [
  "Locating official website…",
  "Checking domain age and SSL…",
  "Searching for customer reviews…",
  "Scanning for adverse media…",
  "Checking social media presence…",
  "Synthesizing findings with AI…",
];

const Index = () => {
  const [currentReport, setCurrentReport]   = useState<DossierReport | null>(null);
  const [pastReports, setPastReports]       = useState<DossierReport[]>([]);
  const [isLoading, setIsLoading]           = useState(false);
  const [loadingStep, setLoadingStep]       = useState(0);
  const [error, setError]                   = useState<string | null>(null);
  const [activeTab, setActiveTab]           = useState("current");

  // Populate Past Reports from DB on page load
  useEffect(() => {
    fetchHistory(20).then(setPastReports).catch(() => {});
  }, []);

  // Cycle through loading messages while analysis is running
  useEffect(() => {
    if (!isLoading) {
      setLoadingStep(0);
      return;
    }
    const interval = setInterval(() => {
      setLoadingStep((s) => Math.min(s + 1, LOADING_STEPS.length - 1));
    }, 4000); // advance every 4s — ~24s to cycle through all steps
    return () => clearInterval(interval);
  }, [isLoading]);

  const handleSearch = async (businessName: string, location: string, forceRefresh = false) => {
    setIsLoading(true);
    setError(null);
    setLoadingStep(0);
    try {
      // submit → poll every 2s → fetch report when complete
      const report = await fetchReport(businessName, location, forceRefresh);
      setCurrentReport(report);
      setPastReports((prev) =>
        [report, ...prev.filter((r) => r.id !== report.id)].slice(0, 20)
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Analysis failed. Make sure the backend is running on port 8000."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleReanalyze = () => {
    if (currentReport) handleSearch(currentReport.businessName, currentReport.location, true);
  };

  const handleSelectPastReport = (report: DossierReport) => {
    setCurrentReport(report);
    setActiveTab("current");
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-5xl px-4 py-8">

        {/* Header */}
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
            <Shield className="h-5 w-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">
              Business Legitimacy Dossier
            </h1>
            <p className="text-xs text-muted-foreground">Analyst due diligence tool</p>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            <TabsTrigger value="current">Current Analysis</TabsTrigger>
            <TabsTrigger value="past">
              Past Reports
              {pastReports.length > 0 && (
                <span className="ml-1.5 rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {pastReports.length}
                </span>
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="current">
            <SearchPanel onSearch={handleSearch} isLoading={isLoading} />

            {/* Polling progress indicator */}
            {isLoading && (
              <div className="mt-8 flex flex-col items-center gap-3">
                <div className="flex gap-1">
                  {LOADING_STEPS.map((_, i) => (
                    <div
                      key={i}
                      className={`h-1.5 w-6 rounded-full transition-colors duration-500 ${
                        i <= loadingStep ? "bg-primary" : "bg-muted"
                      }`}
                    />
                  ))}
                </div>
                <p className="text-sm text-muted-foreground">
                  {LOADING_STEPS[loadingStep]}
                </p>
              </div>
            )}

            {/* Error state */}
            {error && (
              <div className="mt-6 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                {error}
              </div>
            )}

            {/* Report + Re-analyze button */}
            {!isLoading && currentReport && (
              <>
                <div className="mt-6 flex justify-end">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleReanalyze}
                    className="gap-1.5"
                  >
                    <RefreshCw className="h-3.5 w-3.5" /> Re-analyze
                  </Button>
                </div>
                <DossierReportView report={currentReport} />
              </>
            )}

            {/* Empty state */}
            {!isLoading && !currentReport && !error && (
              <div className="mt-16 text-center text-muted-foreground">
                <Shield className="mx-auto mb-3 h-10 w-10 opacity-20" />
                <p className="text-sm">
                  Enter a business name to generate a legitimacy report.
                </p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="past">
            <PastReportsTable
              reports={pastReports}
              onSelect={handleSelectPastReport}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default Index;