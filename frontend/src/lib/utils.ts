import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatScore(score: number): string {
  return (score * 100).toFixed(0);
}

export function confidenceColor(level: string): string {
  switch (level) {
    case "High": return "text-emerald-600";
    case "Moderate": return "text-amber-600";
    case "Low": return "text-red-600";
    default: return "text-slate-500";
  }
}

export function confidenceBg(level: string): string {
  switch (level) {
    case "High": return "bg-emerald-50 border-emerald-200";
    case "Moderate": return "bg-amber-50 border-amber-200";
    case "Low": return "bg-red-50 border-red-200";
    default: return "bg-slate-50 border-slate-200";
  }
}

export function significanceColor(sig: string | null): string {
  if (!sig) return "text-slate-500";
  const s = sig.toLowerCase();
  if (s.includes("pathogenic")) return "text-red-600";
  if (s.includes("benign")) return "text-emerald-600";
  if (s.includes("uncertain")) return "text-amber-600";
  if (s.includes("likely")) return "text-orange-600";
  return "text-slate-600";
}

export function storeRecentSearch(query: string) {
  try {
    const stored = JSON.parse(localStorage.getItem("sydney_recent") || "[]") as string[];
    const updated = [query, ...stored.filter((s) => s !== query)].slice(0, 10);
    localStorage.setItem("sydney_recent", JSON.stringify(updated));
  } catch {}
}

export function getRecentSearches(): string[] {
  try {
    return JSON.parse(localStorage.getItem("sydney_recent") || "[]");
  } catch {
    return [];
  }
}
