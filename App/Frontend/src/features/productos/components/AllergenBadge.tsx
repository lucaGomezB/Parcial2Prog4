/**
 * AllergenBadge — Reusable amber pill badge for allergen indication.
 *
 * Renders an inline `<span>` with amber background that communicates
 * allergen presence at a glance. Used on ProductCard (aggregate indicator)
 * and ProductoDetail (per-ingredient badge).
 *
 * Props:
 *   - label: string — badge text (default: "Alergeno")
 *   - className: string — additional Tailwind classes for style extension
 */
interface AllergenBadgeProps {
  label?: string;
  className?: string;
}

export default function AllergenBadge({ label = "Alergeno", className = "" }: AllergenBadgeProps) {
  return (
    <span
      className={`bg-amber-500 text-gray-800 font-semibold text-xs px-2 py-0.5 rounded-full inline-flex items-center gap-1 ${className}`}
    >
      {label}
    </span>
  );
}
