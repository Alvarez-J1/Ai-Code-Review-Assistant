export type Severity = "low" | "medium" | "high";
export type FindingCategory = "bug" | "edge_case" | "security" | "performance" | "readability" | "testing";
export type FindingSource = "ai" | "deterministic";
export type ReviewInputType = "diff" | "github";
export type ReviewStatus = "completed" | "failed";
export type RiskLevel = "low" | "medium" | "high";

export interface ReviewStats {
  files_reviewed: number;
  findings: number;
  high_severity: number;
  medium_severity: number;
  low_severity: number;
}

export interface GitHubMetadata {
  owner: string;
  repo: string;
  pr_number: number;
  title: string | null;
  state: string | null;
  author: string | null;
  html_url: string;
  base_ref: string | null;
  head_ref: string | null;
  changed_files: number | null;
  additions: number | null;
  deletions: number | null;
}

export interface ReviewFinding {
  file: string;
  line: number | null;
  end_line: number | null;
  category: FindingCategory;
  severity: Severity;
  title: string;
  explanation: string;
  suggestion: string;
  confidence: number;
  source: FindingSource;
}

export interface ReviewResponse {
  review_id: string;
  input_type: ReviewInputType | null;
  github_metadata: GitHubMetadata | null;
  risk_level: RiskLevel;
  summary: string;
  stats: ReviewStats;
  findings: ReviewFinding[];
  created_at: string;
}

export interface ReviewSessionSummary {
  review_id: string;
  input_type: ReviewInputType;
  status: ReviewStatus;
  repository_owner: string | null;
  repository_name: string | null;
  pull_request_number: number | null;
  pull_request_title: string | null;
  pull_request_url: string | null;
  state: string | null;
  risk_level: RiskLevel;
  summary: string;
  stats: ReviewStats;
  created_at: string;
  completed_at: string | null;
}

export interface ReviewListResponse {
  items: ReviewSessionSummary[];
  limit: number;
  offset: number;
  count: number;
}
