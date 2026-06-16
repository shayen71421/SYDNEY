import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Header } from "@/components/layout/Header";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Sydney — Biomedical Variant Intelligence",
  description:
    "AI-powered platform for understanding genetic variants through evidence aggregation from ClinVar, PubMed, and biomedical literature.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          <div className="min-h-screen sydney-gradient">
            <Header />
            <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
