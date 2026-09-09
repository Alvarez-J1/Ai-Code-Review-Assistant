"use client";

import { useEffect, useState } from "react";

const STEPS = [
  "Parsing code changes...",
  "Running deterministic checks...",
  "Analyzing changed code...",
  "Organizing findings...",
  "Finalizing review..."
];

export function LoadingSteps({ active }: { active: boolean }) {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    if (!active) {
      return;
    }

    const id = window.setInterval(() => {
      setStepIndex((current) => (current + 1) % STEPS.length);
    }, 1600);

    return () => window.clearInterval(id);
  }, [active]);

  if (!active) {
    return null;
  }

  return (
    <div aria-atomic="true" className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3" role="status">
      <div className="flex items-center gap-3">
        <span
          aria-hidden="true"
          className="h-4 w-4 shrink-0 rounded-full border-2 border-blue-200 border-t-brand motion-safe:animate-spin"
        />
        <p className="text-sm font-medium text-blue-950">{STEPS[stepIndex]}</p>
      </div>
    </div>
  );
}
