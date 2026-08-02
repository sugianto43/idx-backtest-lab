"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/datasets", label: "Datasets" },
  { href: "/runs", label: "Runs" },
  { href: "/strategies", label: "Strategies" },
  { href: "/system", label: "System status" },
] as const;

export function SiteNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary">
      <ul>
        {NAV_ITEMS.map((item) => {
          const isCurrent = pathname === item.href;
          return (
            <li key={item.href}>
              <Link href={item.href} aria-current={isCurrent ? "page" : undefined}>
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
