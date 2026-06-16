"use client";

import Link from "next/link";
import { FlaskConical, Github } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";

export function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/80 backdrop-blur-sm dark:border-slate-700 dark:bg-slate-900/80">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2">
          <FlaskConical className="h-6 w-6 text-sydney-600" />
          <span className="text-lg font-bold text-slate-900 dark:text-white">
            Sydney
          </span>
        </Link>
        <nav className="flex items-center gap-4">
          <Link
            href="/dashboard"
            className="text-sm text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
          >
            Dashboard
          </Link>
          <Link
            href="/variants"
            className="text-sm text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
          >
            Variants
          </Link>
          <a
            href="https://github.com/shayen71421/SYDNEY"
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-400 hover:text-slate-600"
          >
            <Github className="h-5 w-5" />
          </a>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
