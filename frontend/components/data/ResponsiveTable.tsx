import type { ReactNode } from "react";

export function ResponsiveTable({ caption, children }: { caption: string; children: ReactNode }) {
  return (
    <div className="responsive-table">
      <table>
        <caption>{caption}</caption>
        {children}
      </table>
    </div>
  );
}
