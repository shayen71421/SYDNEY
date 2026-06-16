"use client";

import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "outline" | "success" | "warning" | "danger";
  className?: string;
  onClick?: () => void;
}

export function Badge({ children, variant = "default", className }: BadgeProps) {
  const variants = {
    default: "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300",
    outline: "border border-slate-300 text-slate-600 dark:border-slate-600 dark:text-slate-400",
    success: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300",
    warning: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
    danger: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
