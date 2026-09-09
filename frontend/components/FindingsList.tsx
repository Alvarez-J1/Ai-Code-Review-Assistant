"use client";

import { useId, useMemo, useState } from "react";

import type { FindingCategory, ReviewFinding, Severity } from "@/types/reviews";

const severityOptions: Array<Severity | "all"> = ["all", "high", "medium", "low"];
const categoryOptions: Array<FindingCategory | "all"> = [
  "all",
  "bug",
  "edge_case",
  "security",
  "performance",
  "readability",
  "testing"
];

const severityStyles: Record<Severity, string> = {
  low: "border-emerald-200 bg-emerald-50 text-emerald-950",
  medium: "border-amber-200 bg-amber-50 text-amber-950",
  high: "border-red-200 bg-red-50 text-red-950"
};

const categoryLabels: Record<FindingCategory, string> = {
  bug: "Bug",
  edge_case: "Edge case",
  security: "Security",
  performance: "Performance",
  readability: "Readability",
  testing: "Testing"
};

export function FindingsList({ findings, githubUrl }: { findings: ReviewFinding[]; githubUrl?: string | null }) {
  const [severity, setSeverity] = useState<Severity | "all">("all");
  const [category, setCategory] = useState<FindingCategory | "all">("all");
  const [file, setFile] = useState("all");
  const severityFilterId = useId();
  const categoryFilterId = useId();
  const fileFilterId = useId();

  const files = useMemo(() => Array.from(new Set(findings.map((finding) => finding.file))).sort(), [findings]);
  const visibleFindings = useMemo(
    () =>
      findings.filter((finding) => {
        return (
          (severity === "all" || finding.severity === severity) &&
          (category === "all" || finding.category === category) &&
          (file === "all" || finding.file === file)
        );
      }),
    [category, file, findings, severity]
  );

  if (findings.length === 0) {
    return (
      <section className="rounded-lg border border-line bg-panel p-6">
        <h2 className="text-lg font-semibold text-ink">Findings</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          This review completed without findings. Keep an eye on test coverage and runtime behavior as the change evolves.
        </p>
      </section>
    );
  }

  function resetFilters() {
    setSeverity("all");
    setCategory("all");
    setFile("all");
  }

  return (
    <section className="space-y-4">
      <div className="rounded-lg border border-line bg-panel p-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-ink">Findings</h2>
            <p className="text-sm text-muted">
              Showing {visibleFindings.length} of {findings.length}
            </p>
          </div>
          <fieldset className="grid gap-3 sm:grid-cols-3 lg:min-w-[680px]">
            <legend className="sr-only">Filter findings</legend>
            <FilterSelect id={severityFilterId} label="Severity" onChange={setSeverity} options={severityOptions} value={severity} />
            <FilterSelect id={categoryFilterId} label="Category" onChange={setCategory} options={categoryOptions} value={category} />
            <label className="space-y-1 text-sm font-medium text-ink" htmlFor={fileFilterId}>
              <span>File</span>
              <select
                className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink"
                id={fileFilterId}
                onChange={(event) => setFile(event.target.value)}
                value={file}
              >
                <option value="all">All files</option>
                {files.map((fileName) => (
                  <option key={fileName} value={fileName}>
                    {fileName}
                  </option>
                ))}
              </select>
            </label>
          </fieldset>
          <button
            className="rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:border-brand hover:text-brand"
            onClick={resetFilters}
            type="button"
          >
            Reset Filters
          </button>
        </div>
      </div>

      {visibleFindings.length === 0 ? (
        <div className="rounded-lg border border-dashed border-line bg-panel p-6 text-sm text-muted">
          No findings match the current filters.
        </div>
      ) : (
        <div className="space-y-3">
          {visibleFindings.map((finding, index) => (
            <FindingCard finding={finding} githubUrl={githubUrl} key={`${finding.file}-${finding.line}-${finding.title}-${index}`} />
          ))}
        </div>
      )}
    </section>
  );
}

function FilterSelect<T extends string>({
  id,
  label,
  onChange,
  options,
  value
}: {
  id: string;
  label: string;
  onChange: (value: T) => void;
  options: T[];
  value: T;
}) {
  return (
    <label className="space-y-1 text-sm font-medium text-ink" htmlFor={id}>
      <span>{label}</span>
      <select
        className="w-full rounded-md border border-line bg-white px-3 py-2 text-sm text-ink"
        id={id}
        onChange={(event) => onChange(event.target.value as T)}
        value={value}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option === "all" ? `All ${label.toLowerCase()}` : labelFor(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

function FindingCard({ finding, githubUrl }: { finding: ReviewFinding; githubUrl?: string | null }) {
  return (
    <article className="rounded-lg border border-line bg-panel p-5 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-md border px-2 py-1 text-xs font-bold uppercase ${severityStyles[finding.severity]}`}>
              Severity: {finding.severity}
            </span>
            <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs font-semibold uppercase text-muted">
              {categoryLabels[finding.category]}
            </span>
            <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs font-semibold uppercase text-muted">
              {finding.source}
            </span>
          </div>
          <h3 className="mt-3 text-lg font-semibold text-ink">{finding.title}</h3>
          <p className="mt-2 break-anywhere font-mono text-sm text-muted">
            {finding.file}
            {lineLabel(finding)}
          </p>
        </div>
        <div className="shrink-0 rounded-md border border-line bg-slate-50 px-3 py-2 text-sm font-semibold text-ink">
          {Math.round(finding.confidence * 100)}% confidence
        </div>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <p className="text-sm font-semibold text-ink">Explanation</p>
          <p className="mt-1 text-sm leading-6 text-muted">{finding.explanation}</p>
        </div>
        <div>
          <p className="text-sm font-semibold text-ink">Suggested improvement</p>
          <p className="mt-1 text-sm leading-6 text-muted">{finding.suggestion}</p>
        </div>
      </div>
      {githubUrl ? (
        <a
          className="mt-4 inline-flex rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:border-brand hover:text-brand"
          href={githubUrl}
          rel="noreferrer"
          target="_blank"
        >
          Open PR on GitHub
        </a>
      ) : null}
    </article>
  );
}

function lineLabel(finding: ReviewFinding) {
  if (!finding.line) {
    return "";
  }
  if (finding.end_line && finding.end_line !== finding.line) {
    return `:${finding.line}-${finding.end_line}`;
  }
  return `:${finding.line}`;
}

function labelFor(value: string) {
  if (value in categoryLabels) {
    return categoryLabels[value as FindingCategory];
  }
  return value.charAt(0).toUpperCase() + value.slice(1);
}
