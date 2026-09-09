import { AppShell } from "@/components/AppShell";
import { RecentReviewsClient } from "@/components/RecentReviewsClient";
import { ApiError, listReviews } from "@/lib/api";

const PAGE_SIZE = 10;

export const dynamic = "force-dynamic";

async function loadInitialReviews() {
  try {
    const response = await listReviews(PAGE_SIZE, 0);
    return {
      error: null,
      hasMore: response.count === PAGE_SIZE,
      items: response.items,
      nextOffset: response.count
    };
  } catch (caught) {
    return {
      error: caught instanceof ApiError ? caught.message : "Recent reviews could not be loaded.",
      hasMore: false,
      items: [],
      nextOffset: 0
    };
  }
}

export default async function ReviewsPage() {
  const initialState = await loadInitialReviews();

  return (
    <AppShell>
      <RecentReviewsClient
        initialError={initialState.error}
        initialHasMore={initialState.hasMore}
        initialItems={initialState.items}
        initialOffset={initialState.nextOffset}
      />
    </AppShell>
  );
}
