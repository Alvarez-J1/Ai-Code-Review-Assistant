import { AppShell } from "@/components/AppShell";
import { ReviewDetailClient } from "@/components/ReviewDetailClient";

interface ReviewPageProps {
  params: Promise<{
    id: string;
  }>;
}

export default async function ReviewPage({ params }: ReviewPageProps) {
  const { id } = await params;

  return (
    <AppShell>
      <ReviewDetailClient reviewId={id} />
    </AppShell>
  );
}
