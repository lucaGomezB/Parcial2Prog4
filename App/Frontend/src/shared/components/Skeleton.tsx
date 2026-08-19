/**
 * Skeleton — Reusable loading placeholder components.
 *
 * Provides consistent skeleton patterns for the most common loading states
 * across the project: product cards, table rows, and generic text blocks.
 *
 * Usage:
 *   <ProductCardSkeleton count={8} />
 *   <TableRowSkeleton columns={6} rows={5} />
 *   <TextSkeleton lines={3} />
 */
import type { ReactNode } from 'react'

// ── ProductCardSkeleton ──

interface ProductCardSkeletonProps {
  count?: number
}

export function ProductCardSkeleton({ count = 8 }: ProductCardSkeletonProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-white rounded-lg shadow-md overflow-hidden animate-pulse">
          <div className="w-full aspect-[4/3] bg-gray-200" />
          <div className="p-4 space-y-2">
            <div className="h-4 bg-gray-200 rounded w-3/4" />
            <div className="h-3 bg-gray-200 rounded w-1/2" />
            <div className="h-6 bg-gray-200 rounded w-1/3 mt-2" />
          </div>
        </div>
      ))}
    </div>
  )
}

// ── TableRowSkeleton ──

interface TableRowSkeletonProps {
  columns?: number
  rows?: number
  children?: ReactNode // custom rendering — overrides columns/rows
}

export function TableRowSkeleton({ columns = 6, rows = 5 }: TableRowSkeletonProps) {
  return (
    <div className="animate-pulse">
      {Array.from({ length: rows }).map((_, rowIdx) => (
        <div key={rowIdx} className="flex gap-4 py-3 border-b border-gray-100">
          {Array.from({ length: columns }).map((_, colIdx) => (
            <div
              key={colIdx}
              className="h-4 bg-gray-200 rounded"
              style={{ flex: colIdx === columns - 1 ? 0.5 : 1 }}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

// ── TextSkeleton ──

interface TextSkeletonProps {
  lines?: number
}

export function TextSkeleton({ lines = 3 }: TextSkeletonProps) {
  const widths = ['w-3/4', 'w-full', 'w-1/2', 'w-5/6', 'w-2/3', 'w-1/3']

  return (
    <div className="space-y-2 animate-pulse">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`h-4 bg-gray-200 rounded ${widths[i % widths.length]}`}
        />
      ))}
    </div>
  )
}
