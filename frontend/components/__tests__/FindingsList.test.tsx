import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { FindingsList } from "@/components/FindingsList";
import type { ReviewFinding } from "@/types/reviews";

const findings: ReviewFinding[] = [
  {
    category: "security",
    confidence: 0.95,
    end_line: 42,
    explanation: "The webhook handler accepts unsigned requests from external callers.",
    file: "src/webhooks/stripe.py",
    line: 38,
    severity: "high",
    source: "deterministic",
    suggestion: "Verify the provider signature before parsing the request body.",
    title: "Missing webhook signature verification"
  },
  {
    category: "testing",
    confidence: 0.72,
    end_line: null,
    explanation: "The change adds checkout behavior without a regression test.",
    file: "tests/test_checkout.py",
    line: null,
    severity: "low",
    source: "ai",
    suggestion: "Add a test that covers the declined-payment branch.",
    title: "Add declined-payment coverage"
  }
];

describe("FindingsList", () => {
  it("filters findings by severity without refetching", async () => {
    const user = userEvent.setup();
    render(<FindingsList findings={findings} githubUrl="https://github.com/acme/payments/pull/42" />);

    expect(screen.getByText("Showing 2 of 2")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Severity"), "high");

    expect(screen.getByText("Showing 1 of 2")).toBeInTheDocument();
    expect(screen.getByText("Missing webhook signature verification")).toBeInTheDocument();
    expect(screen.queryByText("Add declined-payment coverage")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open PR on GitHub" })).toHaveAttribute(
      "href",
      "https://github.com/acme/payments/pull/42"
    );
  });

  it("renders a useful zero-findings state", () => {
    render(<FindingsList findings={[]} />);

    expect(screen.getByText("Findings")).toBeInTheDocument();
    expect(screen.getByText(/completed without findings/i)).toBeInTheDocument();
  });
});
