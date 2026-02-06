"use client";

import { usePathname } from "next/navigation";

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/notes": "Notes",
  "/graph": "Knowledge Graph",
  "/agent": "AI Agent",
  "/settings": "Settings",
};

export function Header() {
  const pathname = usePathname();
  const title =
    pageTitles[pathname] ||
    (pathname.startsWith("/notes/") ? "Note Editor" : "OmniMind");

  return (
    <header className="flex h-14 items-center border-b px-6">
      <h1 className="text-lg font-semibold">{title}</h1>
    </header>
  );
}
