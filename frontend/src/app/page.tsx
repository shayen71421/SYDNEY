"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search, FlaskConical, AlertCircle, Clock } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useVariantSearch } from "@/lib/hooks";
import { storeRecentSearch, getRecentSearches } from "@/lib/utils";

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [recent, setRecent] = useState<string[]>([]);
  const searchMutation = useVariantSearch();
  const router = useRouter();

  useEffect(() => {
    setRecent(getRecentSearches());
  }, []);

  function handleSearch() {
    const trimmed = query.trim();
    if (!trimmed) {
      setError("Please enter a variant");
      return;
    }

    const valid = /^(BRCA1|BRCA2|TP53|P53|CDH1|PALB2|CHEK2|ATM|PTEN)\s/i.test(trimmed);
    if (!valid) {
      setError("Format: gene + variant. Example: BRCA1 c.5266dupC, CDH1 c.1901C>T");
      return;
    }

    setError("");
    searchMutation.mutate(trimmed, {
      onSuccess: (data) => {
        storeRecentSearch(trimmed);
        setRecent(getRecentSearches());
        router.push(`/variants/${data.id}`);
      },
      onError: (err: Error) => {
        setError(err.message);
      },
    });
  }

  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="mb-8 text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-sydney-100 dark:bg-sydney-900">
          <FlaskConical className="h-8 w-8 text-sydney-600" />
        </div>
        <h1 className="text-4xl font-bold text-slate-900 dark:text-white">
          Sydney
        </h1>
        <p className="mt-2 text-lg text-slate-500 dark:text-slate-400">
          Biomedical Variant Intelligence Platform
        </p>
      </div>

      <div className="w-full max-w-2xl">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setError("");
            }}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Enter a variant... e.g. BRCA1 c.5266dupC, TP53 R175H, CDH1 c.1901C>T"
            className="w-full rounded-lg border border-slate-300 bg-white py-3 pl-10 pr-4 text-sm shadow-sm placeholder:text-slate-400 focus:border-sydney-500 focus:outline-none focus:ring-2 focus:ring-sydney-500/20 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:placeholder:text-slate-500"
          />
        </div>

        {error && (
          <div className="mt-3 flex items-center gap-2 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {searchMutation.isPending && (
          <div className="mt-4 flex items-center justify-center gap-2 text-sm text-slate-500">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-sydney-500 border-t-transparent" />
            Searching databases...
          </div>
        )}

        <div className="mt-4 flex justify-center">
          <Button onClick={handleSearch} size="lg" loading={searchMutation.isPending}>
            <Search className="mr-2 h-4 w-4" />
            Search Variant
          </Button>
        </div>
      </div>

      <div className="mt-8 flex flex-wrap justify-center gap-2">
        <span
          className="cursor-pointer text-xs text-slate-400 underline hover:text-slate-600"
          onClick={() => setQuery("BRCA1 c.5266dupC")}
        >
          BRCA1 c.5266dupC
        </span>
        <span
          className="cursor-pointer text-xs text-slate-400 underline hover:text-slate-600"
          onClick={() => setQuery("TP53 R175H")}
        >
          TP53 R175H
        </span>
        <span
          className="cursor-pointer text-xs text-slate-400 underline hover:text-slate-600"
          onClick={() => setQuery("BRCA2 c.5946delT")}
        >
          BRCA2 c.5946delT
        </span>
        <span
          className="cursor-pointer text-xs text-slate-400 underline hover:text-slate-600"
          onClick={() => setQuery("CDH1 c.1901C>T")}
        >
          CDH1 c.1901C&gt;T
        </span>
        <span
          className="cursor-pointer text-xs text-slate-400 underline hover:text-slate-600"
          onClick={() => setQuery("PALB2 c.1592delT")}
        >
          PALB2 c.1592delT
        </span>
      </div>

      {recent.length > 0 && (
        <Card className="mt-8 w-full max-w-md">
          <CardContent>
            <div className="mb-2 flex items-center gap-2 text-sm text-slate-500">
              <Clock className="h-4 w-4" />
              Recent Searches
            </div>
            <div className="flex flex-wrap gap-2">
              {recent.map((q, i) => (
                <Badge
                  key={i}
                  variant="outline"
                  className="cursor-pointer"
                  onClick={() => {
                    setQuery(q);
                  }}
                >
                  {q}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
