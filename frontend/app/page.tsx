import { AppShell } from "@/components/AppShell";
import { ReviewForm } from "@/components/ReviewForm";

export default function HomePage() {
  return (
    <AppShell>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-brand">New review</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-normal text-ink">Review changed code before it ships</h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-muted">
              Paste a unified diff or submit a GitHub pull request URL. The backend parses the changes, runs deterministic checks, asks for structured AI findings, and saves the result.
            </p>
          </div>
          <ReviewForm />
        </div>
        <aside className="space-y-3">
          <div className="rounded-lg border border-line bg-panel p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Review pipeline</h2>
            <ol className="mt-3 space-y-3 text-sm text-ink">
              {["Parse diff", "Preprocess chunks", "Run deterministic checks", "Analyze with OpenAI", "Deduplicate findings"].map((step) => (
                <li className="flex gap-3" key={step}>
                  <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-blue-100 text-center text-xs font-bold leading-5 text-brand">
                    {step.charAt(0)}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>
          <div className="rounded-lg border border-line bg-panel p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Finding categories</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {["bug", "edge case", "security", "performance", "readability", "testing"].map((category) => (
                <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs font-semibold text-muted" key={category}>
                  {category}
                </span>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </AppShell>
  );
}
