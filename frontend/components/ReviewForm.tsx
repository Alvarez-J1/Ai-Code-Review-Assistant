"use client";

import type { FormEvent, KeyboardEvent, ReactNode, RefObject } from "react";
import { useEffect, useId, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError, createDiffReview, createGithubReview } from "@/lib/api";
import { LoadingSteps } from "@/components/LoadingSteps";

type ReviewMode = "diff" | "github";

const DIFF_PLACEHOLDER = `diff --git a/src/app.py b/src/app.py
index 1111111..2222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1,3 +1,4 @@
 def run():
+    print("debug")
     return True`;

export function ReviewForm() {
  const router = useRouter();
  const diffTabId = useId();
  const githubTabId = useId();
  const diffPanelId = useId();
  const githubPanelId = useId();
  const diffTabRef = useRef<HTMLButtonElement>(null);
  const githubTabRef = useRef<HTMLButtonElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);
  const [mode, setMode] = useState<ReviewMode>("diff");
  const [diff, setDiff] = useState("");
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submitReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const validationError = validateInput(mode, mode === "diff" ? diff : url);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    try {
      const review = mode === "diff" ? await createDiffReview(diff.trim()) : await createGithubReview(url.trim());
      router.push(`/reviews/${review.review_id}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The review could not be created. Try again.");
      setIsSubmitting(false);
    }
  }

  useEffect(() => {
    if (error) {
      errorRef.current?.focus();
    }
  }, [error]);

  function selectMode(nextMode: ReviewMode) {
    setMode(nextMode);
    window.requestAnimationFrame(() => {
      const nextTab = nextMode === "diff" ? diffTabRef : githubTabRef;
      nextTab.current?.focus();
    });
  }

  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    const nextMode = mode === "diff" ? "github" : "diff";
    const targetMode = event.key === "Home" ? "diff" : event.key === "End" ? "github" : nextMode;

    if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
      event.preventDefault();
      selectMode(targetMode);
    }
  }

  return (
    <section className="rounded-lg border border-line bg-panel shadow-soft">
      <div className="border-b border-line px-4 pt-4 sm:px-6">
        <div aria-label="Review input type" aria-orientation="horizontal" className="flex w-full gap-2" role="tablist">
          <TabButton
            active={mode === "diff"}
            controlsId={diffPanelId}
            disabled={isSubmitting}
            id={diffTabId}
            onClick={() => selectMode("diff")}
            onKeyDown={handleTabKeyDown}
            tabRef={diffTabRef}
          >
            Paste Diff
          </TabButton>
          <TabButton
            active={mode === "github"}
            controlsId={githubPanelId}
            disabled={isSubmitting}
            id={githubTabId}
            onClick={() => selectMode("github")}
            onKeyDown={handleTabKeyDown}
            tabRef={githubTabRef}
          >
            GitHub PR
          </TabButton>
        </div>
      </div>

      <form aria-busy={isSubmitting} className="space-y-5 p-4 sm:p-6" noValidate onSubmit={submitReview}>
        {mode === "diff" ? (
          <div aria-labelledby={diffTabId} className="space-y-2" id={diffPanelId} role="tabpanel">
            <label className="text-sm font-semibold text-ink" htmlFor="diff-input">
              Unified git diff
            </label>
            <textarea
              aria-describedby={error ? "review-error" : undefined}
              className="min-h-[360px] w-full resize-y rounded-md border border-line bg-white px-3 py-3 font-mono text-sm leading-6 text-ink shadow-sm transition placeholder:text-slate-400 focus:border-brand"
              disabled={isSubmitting}
              id="diff-input"
              name="diff"
              onChange={(event) => setDiff(event.target.value)}
              placeholder={DIFF_PLACEHOLDER}
              required
              spellCheck={false}
              value={diff}
            />
          </div>
        ) : (
          <div aria-labelledby={githubTabId} className="space-y-2" id={githubPanelId} role="tabpanel">
            <label className="text-sm font-semibold text-ink" htmlFor="github-url">
              GitHub pull request URL
            </label>
            <input
              aria-describedby={error ? "review-error github-note" : "github-note"}
              className="w-full rounded-md border border-line bg-white px-3 py-3 font-mono text-sm text-ink shadow-sm transition placeholder:text-slate-400 focus:border-brand"
              disabled={isSubmitting}
              id="github-url"
              name="github-url"
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://github.com/owner/repository/pull/123"
              required
              spellCheck={false}
              type="url"
              autoComplete="url"
              value={url}
            />
            <p className="text-sm text-muted" id="github-note">
              Public PRs can be reviewed without OAuth. A configured backend token may raise GitHub API limits.
            </p>
          </div>
        )}

        {error ? (
          <div
            className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-900"
            aria-atomic="true"
            id="review-error"
            ref={errorRef}
            role="alert"
            tabIndex={-1}
          >
            {error}
          </div>
        ) : null}

        <LoadingSteps active={isSubmitting} />

        <div className="flex flex-col gap-3 border-t border-line pt-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-muted" id="review-save-note">
            Reviews are saved by the backend after analysis, so results can be reopened from Recent Reviews.
          </p>
          <button
            aria-describedby="review-save-note"
            className="rounded-md bg-ink px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand disabled:cursor-not-allowed disabled:bg-slate-400"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Review Running" : mode === "diff" ? "Review Diff" : "Review PR"}
          </button>
        </div>
      </form>
    </section>
  );
}

function TabButton({
  active,
  children,
  controlsId,
  disabled,
  id,
  onClick,
  onKeyDown,
  tabRef
}: {
  active: boolean;
  children: ReactNode;
  controlsId: string;
  disabled: boolean;
  id: string;
  onClick: () => void;
  onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => void;
  tabRef: RefObject<HTMLButtonElement | null>;
}) {
  return (
    <button
      aria-controls={controlsId}
      aria-selected={active}
      className={`rounded-t-md border border-b-0 px-4 py-2.5 text-sm font-semibold transition ${
        active
          ? "border-line bg-panel text-ink"
          : "border-transparent bg-transparent text-muted hover:bg-slate-100 hover:text-ink"
      }`}
      disabled={disabled}
      id={id}
      onClick={onClick}
      onKeyDown={onKeyDown}
      ref={tabRef}
      role="tab"
      tabIndex={active ? 0 : -1}
      type="button"
    >
      {children}
    </button>
  );
}

function validateInput(mode: ReviewMode, value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return mode === "diff" ? "Paste a unified git diff before starting a review." : "Enter a GitHub pull request URL.";
  }

  if (mode === "github") {
    try {
      const parsed = new URL(trimmed);
      const parts = parsed.pathname.split("/").filter(Boolean);
      if (parsed.hostname !== "github.com" || parts.length !== 4 || parts[2] !== "pull" || !/^[1-9]\d*$/.test(parts[3])) {
        return "Enter a URL like https://github.com/owner/repository/pull/123.";
      }
    } catch {
      return "Enter a valid GitHub pull request URL.";
    }
  }

  return null;
}
