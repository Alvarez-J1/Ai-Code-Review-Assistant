import Link from "next/link";

import { PrimaryNav } from "@/components/PrimaryNav";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen">
      <a
        className="sr-only rounded-md bg-ink px-3 py-2 text-sm font-semibold text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50"
        href="#main-content"
      >
        Skip to main content
      </a>
      <header className="border-b border-line/80 bg-white/86 backdrop-blur">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <Link className="group flex min-w-0 items-center gap-3" href="/">
            <span
              aria-hidden="true"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-ink text-sm font-semibold text-white"
            >
              AI
            </span>
            <span className="min-w-0">
              <span className="block text-base font-semibold text-ink">AI Code Review Assistant</span>
              <span className="block text-sm text-muted">Structured review for diffs and PRs</span>
            </span>
          </Link>
          <PrimaryNav />
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8" id="main-content">
        {children}
      </main>
    </div>
  );
}
