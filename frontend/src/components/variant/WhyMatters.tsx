"use client";

import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useWhyMatters } from "@/lib/hooks";

interface Props {
  variantId: number;
}

export function WhyMatters({ variantId }: Props) {
  const mutation = useWhyMatters();

  const loading = mutation.isPending;
  const data = mutation.data?.explanation;
  const error = mutation.isError;

  return (
    <div>
      {!data && !loading && !error && (
        <Button size="sm" onClick={() => mutation.mutate(variantId)}>
          <Sparkles className="mr-2 h-4 w-4" />
          Generate Explanation
        </Button>
      )}
      {loading && (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-sydney-500 border-t-transparent" />
          Generating explanation...
        </div>
      )}
      {error && (
        <p className="text-sm text-red-500">
          Failed to generate explanation.
        </p>
      )}
      {data && !loading && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/50">
          <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
            {data}
          </p>
        </div>
      )}
    </div>
  );
}
