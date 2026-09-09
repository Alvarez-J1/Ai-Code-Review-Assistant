import type { ReviewListResponse, ReviewResponse } from "@/types/reviews";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function createDiffReview(diff: string): Promise<ReviewResponse> {
  return request<ReviewResponse>("/reviews/diff", {
    method: "POST",
    body: JSON.stringify({ diff })
  });
}

export async function createGithubReview(url: string): Promise<ReviewResponse> {
  return request<ReviewResponse>("/reviews/github", {
    method: "POST",
    body: JSON.stringify({ url })
  });
}

export async function getReview(reviewId: string): Promise<ReviewResponse> {
  return request<ReviewResponse>(`/reviews/${encodeURIComponent(reviewId)}`);
}

export async function listReviews(limit = 20, offset = 0): Promise<ReviewListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset)
  });
  return request<ReviewListResponse>(`/reviews?${params.toString()}`);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init.headers
      },
      cache: "no-store"
    });
  } catch {
    throw new ApiError("The backend is unavailable. Check that FastAPI is running and try again.", 0);
  }

  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }

  return response.json() as Promise<T>;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body.detail)) {
      return "The request was not valid. Check the highlighted input and try again.";
    }
  } catch {
    return "The request failed. Try again in a moment.";
  }

  if (response.status === 404) {
    return "That review could not be found.";
  }
  if (response.status >= 500) {
    return "The backend could not complete the request. Try again in a moment.";
  }
  return "The request was not valid. Check the input and try again.";
}

function apiBaseUrl(): string {
  const serverBaseUrl = typeof window === "undefined" ? process.env.API_INTERNAL_BASE_URL : undefined;
  return (serverBaseUrl || process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, "");
}
