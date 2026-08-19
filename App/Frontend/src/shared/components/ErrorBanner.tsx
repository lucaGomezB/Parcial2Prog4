/**
 * ErrorBanner — Unified error banner component.
 *
 * Renders a red-tinted banner when `isError` is true, displaying either
 * `error.message` or a custom `message` string. Returns null otherwise.
 *
 * Usage:
 *   <ErrorBanner isError={isError} error={error} message="Custom message" />
 */
import type { ReactNode } from "react";

export interface ErrorBannerProps {
  /** Whether an error state is active. */
  isError: boolean;
  /** Error object whose `.message` will be displayed. */
  error?: Error | null;
  /** Fallback message if error is undefined or has no message. */
  message?: string;
}

export default function ErrorBanner({ isError, error, message }: ErrorBannerProps): ReactNode {
  if (!isError) return null;

  const text = error?.message || message || "Error inesperado";

  return (
    <div className="bg-red-100 text-red-700 p-2 mb-4 rounded">
      {text}
    </div>
  );
}
