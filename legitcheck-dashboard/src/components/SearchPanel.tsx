import { useState } from "react";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface SearchPanelProps {
  onSearch: (businessName: string, location: string) => void;
  isLoading: boolean;
}

const SearchPanel = ({ onSearch, isLoading }: SearchPanelProps) => {
  const [businessName, setBusinessName] = useState("");
  const [location, setLocation] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (businessName.trim().length < 3) {
      setError("Business name must be at least 3 characters.");
      return;
    }
    setError("");
    onSearch(businessName.trim(), location.trim());
  };

  return (
    <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        Business Lookup
      </h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label className="mb-1 block text-xs font-medium text-muted-foreground">
            Business Name *
          </label>
          <Input
            value={businessName}
            onChange={(e) => setBusinessName(e.target.value)}
            placeholder="e.g. Acme Corp"
            required
          />
        </div>
        <div className="flex-1">
          <label className="mb-1 block text-xs font-medium text-muted-foreground">
            Location (optional)
          </label>
          <Input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. New York, NY"
          />
        </div>
        {error && <p className="text-xs text-red-500 sm:col-span-2">{error}</p>}
        <Button type="submit" disabled={!businessName.trim() || isLoading} className="gap-2">
          <Search className="h-4 w-4" />
          {isLoading ? "Generating..." : "Generate Report"}
        </Button>
      </form>
    </div>
  );
};

export default SearchPanel;
