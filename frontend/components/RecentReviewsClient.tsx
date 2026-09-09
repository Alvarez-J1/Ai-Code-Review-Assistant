"use client";

import Link from "next/link";
import { useState } from "react";

import { ReviewListItem } from "@/components/ReviewSummaryPanel";
import { ApiError, listReviews } from "@/lib/api";
import type { ReviewSessionSummary } from "@/types/reviews";

const PAGE_SIZE = 10;

type RecentReviewsClientProps = {
  initialError: string | null;
  initialHasMore: boolean;
  initialItems: ReviewSessionSummary[];
  initialOffset: number;
};

export function RecentReviewsClient({
  initialError,
  initialHasMore,
  initialItems,
  initialOffset
}: RecentReviewsClientProps) {
  const [items, setItems] = useState<ReviewSessionSummary[]>(initialItems);
  const [offset, setOffset] = useState(initialOffset);
  const [error, setError] = useState<string | null>(initialError);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(initialHasMore);

  async function loadPage(nextOffset: number) {
    setError(null);
    setIsLoadingMore(true);
    try {
      const response = await listReviews(PAGE_SIZE, nextOffset);
      setItems((current) => [...current, ...response.items]);
      setOffset(nextOffset + response.count);
      setHasMore(response.count === PAGE_SIZE);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Recent reviews could not be loaded.");
    } finally {
      setIsLoadingMore(false);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Recent Reviews</h1>
          <p className="mt-1 text-sm text-muted">Stored review sessions from the backend.</p>
        </div>
        <Link className="rounded-md bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand" href="/">
          New Review
        </Link>
      </div>

      {error ? (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-900" role="alert">
          {error}
        </div>
      ) : null}

      {items.length === 0 && !error ? (
        <div className="rounded-lg border border-dashed border-line bg-panel p-8 text-center">
          <h2 className="text-lg font-semibold text-ink">No reviews yet</h2>
          <p className="mt-2 text-sm text-muted">Create a pasted-diff or GitHub PR review and it will appear here.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((review) => (
            <Link className="block" href={`/reviews/${review.review_id}`} key={review.review_id}>
              <ReviewListItem review={review} />
            </Link>
          ))}
        </div>
      )}

      {hasMore ? (
        <button
          className="w-full rounded-md border border-line bg-white px-4 py-3 text-sm font-semibold text-ink transition hover:border-brand hover:text-brand disabled:cursor-not-allowed disabled:text-muted"
          disabled={isLoadingMore}
          onClick={() => loadPage(offset)}
          type="button"
        >
          {isLoadingMore ? "Loading..." : "Load More"}
        </button>
      ) : null}
    </section>
  );
}
