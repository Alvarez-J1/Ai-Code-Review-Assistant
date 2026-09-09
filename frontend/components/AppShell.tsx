import Link from "next/link";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-line/80 bg-white/86 backdrop-blur">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <Link className="group flex min-w-0 items-center gap-3" href="/">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-ink text-sm font-semibold text-white">
              AI
            </span>
            <span className="min-w-0">
              <span className="block text-base font-semibold text-ink">AI Code Review Assistant</span>
              <span className="block text-sm text-muted">Structured review for diffs and PRs</span>
            </span>
          </Link>
          <nav aria-label="Primary navigation" className="flex gap-2">
            <Link
              className="rounded-md border border-line bg-white px-3 py-2 text-sm font-medium text-ink transition hover:border-brand hover:text-brand"
              href="/"
            >
              New Review
            </Link>
            <Link
              className="rounded-md border border-line bg-white px-3 py-2 text-sm font-medium text-ink transition hover:border-brand hover:text-brand"
              href="/reviews"
            >
              Recent Reviews
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
    </div>
  );
}
