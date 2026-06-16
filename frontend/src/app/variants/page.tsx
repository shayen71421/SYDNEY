"use client";

import Link from "next/link";
import { useVariants } from "@/lib/hooks";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Dna } from "lucide-react";

export default function VariantsListPage() {
  const { data: variants, isLoading } = useVariants();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-sydney-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Variants
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          All analyzed genetic variants
        </p>
      </div>

      {variants && variants.length > 0 ? (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {variants.map((v) => (
            <Link key={v.id} href={`/variants/${v.id}`}>
              <Card className="transition-colors hover:border-sydney-500">
                <CardContent>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-semibold text-slate-900 dark:text-white">
                        {v.gene} {v.hgvs_c || v.protein_change || ""}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">{v.gene}</p>
                    </div>
                    <Dna className="h-5 w-5 text-slate-400" />
                  </div>
                  <div className="mt-3">
                    <Badge
                      variant={
                        v.clinical_significance?.toLowerCase().includes("pathogenic")
                          ? "danger"
                          : v.clinical_significance?.toLowerCase().includes("benign")
                          ? "success"
                          : "outline"
                      }
                    >
                      {v.clinical_significance || "Pending"}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center text-sm text-slate-500">
            No variants analyzed yet.
            <br />
            <Link href="/" className="mt-2 inline-block text-sydney-600 hover:underline">
              Search for a variant
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
