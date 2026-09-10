import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ReviewSummaryPanel } from "@/components/ReviewSummaryPanel";
import type { ReviewResponse } from "@/types/reviews";

const review: ReviewResponse = {
  created_at: "2026-09-09T04:00:00Z",
  findings: [],
  github_metadata: {
    additions: 28,
    author: "octocat",
    base_ref: "main",
    changed_files: 3,
    deletions: 6,
    head_ref: "feature/review-ui",
    html_url: "https://github.com/acme/review-app/pull/12",
    owner: "acme",
    pr_number: 12,
    repo: "review-app",
    state: "open",
    title: "Improve review findings display"
  },
  input_type: "github",
  review_id: "00000000-0000-4000-8000-000000000012",
  risk_level: "high",
  stats: {
    files_reviewed: 3,
    findings: 4,
    high_severity: 1,
    low_severity: 1,
    medium_severity: 2
  },
  summary: "Reviewed three files and found four issues."
};

describe("ReviewSummaryPanel", () => {
  it("renders risk, stats, summary, and GitHub metadata", () => {
    render(<ReviewSummaryPanel review={review} />);

    expect(screen.getByText("Risk: high")).toBeInTheDocument();
    expect(screen.getByText("Reviewed three files and found four issues.")).toBeInTheDocument();
    expect(screen.getByText("Files reviewed")).toBeInTheDocument();
    expect(screen.getByText("High severity")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open GitHub pull request acme/review-app #12" })).toHaveAttribute(
      "href",
      "https://github.com/acme/review-app/pull/12"
    );
    expect(screen.getByText("Improve review findings display")).toBeInTheDocument();
  });
});
