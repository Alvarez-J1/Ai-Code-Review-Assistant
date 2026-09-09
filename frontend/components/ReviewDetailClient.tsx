"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { FindingsList } from "@/components/FindingsList";
import { ReviewSummaryPanel } from "@/components/ReviewSummaryPanel";
import { ApiError, getReview } from "@/lib/api";
import type { ReviewResponse } from "@/types/reviews";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function ReviewDetailClient({ reviewId }: { reviewId: string }) {
  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isValidId = useMemo(() => UUID_RE.test(reviewId), [reviewId]);

  useEffect(() => {
    if (!isValidId) {
      return;
    }

    let cancelled = false;

    async function loadReview() {
      try {
        const result = await getReview(reviewId);
        if (!cancelled) {
          setReview(result);
        }
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.message : "The review could not be loaded.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadReview();
    return () => {
      cancelled = true;
    };
  }, [isValidId, reviewId]);

  if (!isValidId) {
    return (
      <section className="rounded-lg border border-red-200 bg-red-50 p-6">
        <h1 className="text-xl font-semibold text-red-950">Review unavailable</h1>
        <p className="mt-2 text-sm leading-6 text-red-900">This review ID is not valid.</p>
        <Link className="mt-4 inline-flex rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white" href="/">
          Start a new review
        </Link>
      </section>
    );
  }

  if (isLoading) {
    return <DetailSkeleton />;
  }

  if (error || !review) {
    return (
      <section className="rounded-lg border border-red-200 bg-red-50 p-6">
        <h1 className="text-xl font-semibold text-red-950">Review unavailable</h1>
        <p className="mt-2 text-sm leading-6 text-red-900">{error ?? "That review could not be found."}</p>
        <Link className="mt-4 inline-flex rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white" href="/">
          Start a new review
        </Link>
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <ReviewSummaryPanel review={review} />
      <FindingsList findings={review.findings} githubUrl={review.github_metadata?.html_url} />
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-4" aria-live="polite">
      <div className="rounded-lg border border-line bg-panel p-6">
        <div className="h-5 w-40 animate-pulse rounded bg-slate-200" />
        <div className="mt-4 h-8 w-72 max-w-full animate-pulse rounded bg-slate-200" />
        <div className="mt-4 h-4 w-full animate-pulse rounded bg-slate-200" />
        <div className="mt-2 h-4 w-3/4 animate-pulse rounded bg-slate-200" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <div className="h-24 animate-pulse rounded-lg bg-slate-200" key={index} />
        ))}
      </div>
    </div>
  );
}
