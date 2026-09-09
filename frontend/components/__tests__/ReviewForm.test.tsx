import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const pushMock = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock
  })
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    createDiffReview: vi.fn(),
    createGithubReview: vi.fn()
  };
});

import { ReviewForm } from "@/components/ReviewForm";
import { ApiError, createDiffReview, createGithubReview } from "@/lib/api";

const mockedCreateDiffReview = vi.mocked(createDiffReview);
const mockedCreateGithubReview = vi.mocked(createGithubReview);

describe("ReviewForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows validation for an empty pasted diff", async () => {
    const user = userEvent.setup();
    render(<ReviewForm />);

    await user.click(screen.getByRole("button", { name: "Review Diff" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Paste a unified git diff before starting a review.");
    expect(mockedCreateDiffReview).not.toHaveBeenCalled();
  });

  it("shows validation for an invalid GitHub PR URL", async () => {
    const user = userEvent.setup();
    render(<ReviewForm />);

    await user.click(screen.getByRole("tab", { name: "GitHub PR" }));
    await user.type(screen.getByLabelText("GitHub pull request URL"), "https://gitlab.com/acme/app/pull/1");
    await user.click(screen.getByRole("button", { name: "Review PR" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Enter a URL like https://github.com/owner/repository/pull/123.");
    expect(mockedCreateGithubReview).not.toHaveBeenCalled();
  });

  it("renders a safe API error message", async () => {
    const user = userEvent.setup();
    mockedCreateDiffReview.mockRejectedValueOnce(new ApiError("The backend is unavailable.", 0));
    render(<ReviewForm />);

    await user.type(screen.getByLabelText("Unified git diff"), "diff --git a/src/app.py b/src/app.py");
    await user.click(screen.getByRole("button", { name: "Review Diff" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The backend is unavailable.");
    expect(pushMock).not.toHaveBeenCalled();
  });
});
