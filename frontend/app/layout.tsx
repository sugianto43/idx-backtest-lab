import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "IDX Backtesting Lab",
  description:
    "Local-first research tooling for transparent, reproducible backtests of Indonesia Stock Exchange (IDX) equities.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
