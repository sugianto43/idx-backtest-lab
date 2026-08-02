import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { SiteNav } from "@/components/layout/SiteNav";
import "./globals.css";

export const metadata: Metadata = {
  title: "IDX Backtesting Lab",
  description:
    "Local-first research tooling for transparent, reproducible backtests of Indonesia Stock Exchange (IDX) equities.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">
          Skip to main content
        </a>
        <header>
          <SiteNav />
        </header>
        <main id="main-content">{children}</main>
        <footer>
          <Disclaimer />
        </footer>
      </body>
    </html>
  );
}
