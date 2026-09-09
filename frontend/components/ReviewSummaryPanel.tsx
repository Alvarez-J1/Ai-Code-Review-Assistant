import type { ReviewResponse, ReviewSessionSummary, RiskLevel, Severity } from "@/types/reviews";

const riskStyles: Record<RiskLevel, string> = {
  low: "border-emerald-200 bg-emerald-50 text-emerald-950",
  medium: "border-amber-200 bg-amber-50 text-amber-950",
  high: "border-red-200 bg-red-50 text-red-950"
};

export function ReviewSummaryPanel({ review }: { review: ReviewResponse }) {
  return (
    <section className="space-y-4">
      <div className={`rounded-lg border px-5 py-4 ${riskStyles[review.risk_level]}`}>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide">Risk: {review.risk_level}</p>
            <h1 className="mt-1 text-2xl font-semibold text-ink">Review Results</h1>
          </div>
          <p className="text-sm text-muted">{formatDate(review.created_at)}</p>
        </div>
        <p className="mt-3 max-w-4xl text-base leading-7 text-ink">{review.summary}</p>
      </div>

      {review.github_metadata ? (
        <div className="rounded-lg border border-line bg-panel p-5">
          <p className="text-sm font-semibold text-muted">GitHub pull request</p>
          <div className="mt-2 flex flex-col gap-1">
            <a
              className="break-anywhere text-base font-semibold text-brand hover:underline"
              href={review.github_metadata.html_url}
              rel="noreferrer"
              target="_blank"
            >
              {review.github_metadata.owner}/{review.github_metadata.repo} #{review.github_metadata.pr_number}
            </a>
            {review.github_metadata.title ? <p className="text-sm text-ink">{review.github_metadata.title}</p> : null}
            <p className="text-sm text-muted">
              {review.github_metadata.base_ref ?? "base"} to {review.github_metadata.head_ref ?? "head"}
              {review.github_metadata.state ? ` - ${review.github_metadata.state}` : ""}
            </p>
          </div>
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Metric label="Files reviewed" value={review.stats.files_reviewed} />
        <Metric label="Total findings" value={review.stats.findings} />
        <Metric label="High severity" severity="high" value={review.stats.high_severity} />
        <Metric label="Medium severity" severity="medium" value={review.stats.medium_severity} />
        <Metric label="Low severity" severity="low" value={review.stats.low_severity} />
      </div>
    </section>
  );
}

export function ReviewListItem({ review }: { review: ReviewSessionSummary }) {
  const label = review.input_type === "github" && review.repository_owner && review.repository_name
    ? `${review.repository_owner}/${review.repository_name}${review.pull_request_number ? ` #${review.pull_request_number}` : ""}`
    : "Pasted diff";

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-line bg-panel p-4 transition hover:border-brand hover:shadow-soft sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-md border px-2 py-1 text-xs font-semibold uppercase ${riskStyles[review.risk_level]}`}>
            {review.risk_level}
          </span>
          <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs font-semibold uppercase text-muted">
            {review.input_type}
          </span>
        </div>
        <p className="break-anywhere text-base font-semibold text-ink">{label}</p>
        {review.pull_request_title ? <p className="break-anywhere text-sm text-muted">{review.pull_request_title}</p> : null}
        <p className="line-clamp-2 text-sm leading-6 text-muted">{review.summary}</p>
      </div>
      <div className="shrink-0 text-sm text-muted sm:text-right">
        <p>{review.stats.findings} findings</p>
        <p>{formatDate(review.created_at)}</p>
      </div>
    </div>
  );
}

function Metric({ label, severity, value }: { label: string; severity?: Severity; value: number }) {
  const accent = severity ? severityStyles[severity] : "border-line bg-panel text-ink";
  return (
    <div className={`rounded-lg border p-4 ${accent}`}>
      <p className="text-sm font-medium">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

const severityStyles: Record<Severity, string> = {
  low: "border-emerald-200 bg-emerald-50 text-emerald-950",
  medium: "border-amber-200 bg-amber-50 text-amber-950",
  high: "border-red-200 bg-red-50 text-red-950"
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}
