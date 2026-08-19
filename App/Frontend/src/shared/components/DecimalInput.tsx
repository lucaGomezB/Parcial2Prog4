/**
 * DecimalInput — A controlled numeric input that uses type="text" with
 * inputMode="decimal" to avoid the browser's native number-input bugs
 * (e.g., destroying decimal points during typing).
 *
 * Internal state is a raw string. On blur, the raw string is parsed,
 * clamped, rounded, and committed via onChange. While focused, the
 * raw text is preserved as-is so the user can type freely.
 *
 * Accepts both "." and "," as decimal separators. When both are present,
 * the last occurrence is treated as the decimal separator and the other
 * as a thousands separator (stripped). Examples:
 *   "1,5"     → 1.5    (comma as decimal)
 *   "1.500,50" → 1500.5 (comma = decimal, dot = thousands)
 *   "1,500.50" → 1500.5 (dot = decimal, comma = thousands)
 *   "1500.5"  → 1500.5 (dot as decimal)
 */
import { useState, useEffect, useRef } from "react";

// ── Types ──

interface DecimalInputProps {
  value: number;
  onChange: (value: number) => void;
  onBlur?: () => void;
  disabled?: boolean;
  className?: string;
  placeholder?: string;
  decimals?: number;      // default 2
  min?: number;
  max?: number;
  step?: number;          // accepted but not used on <input type="text">
  isCurrency?: boolean;   // default false
  width?: string;         // default "min-w-[10ch]"
  id?: string;
}

// ── Helpers ──

function formatNumber(value: number, decimals: number, isCurrency: boolean): string {
  if (isCurrency) {
    return value.toLocaleString("es-AR", { style: "currency", currency: "ARS" });
  }
  return Number(value).toFixed(decimals);
}

/**
 * Normalize a user-typed number string to a JavaScript-parseable format.
 *
 * Handles both "." and "," as decimal separators:
 *   - If both "," and "." are present → last one is decimal, other is thousands (stripped)
 *   - If only "," is present → treat as decimal (Convención Argentina)
 *   - If only "." is present → already correct
 */
function normalizeDecimal(raw: string): string {
  let s = raw.trim();

  // ── Heuristic: single separator followed by exactly 3 digits → thousands ──
  // Argentine convention: "1.000" or "1,000" means 1000 (Separador de miles),
  // not 1.0 (decimal). A separator followed by 1-2 digits is the decimal marker.
  // Se usa regex para identificar los separadores
  const dots = (s.match(/\./g) || []).length; 
  const commas = (s.match(/,/g) || []).length;
  const totalSeps = dots + commas;

  if (totalSeps === 1) {
    const sepIdx = Math.max(s.lastIndexOf("."), s.lastIndexOf(","));
    const afterSep = s.slice(sepIdx + 1);
    // Exactly three digits after the separator → thousands separator, remove it
    if (afterSep.length === 3 && /^\d{3}$/.test(afterSep)) {
      return s.replace(/[.,]/g, ""); // "1.000" → "1000", "1,000" → "1000"
    }
    // 1-2 digits or non-digit → fall through to existing logic (decimal separator)
  }

  const lastDot   = s.lastIndexOf(".");
  const lastComma = s.lastIndexOf(",");

  if (lastDot >= 0 && lastComma >= 0) {
    // Both present: last one is the decimal separator
    if (lastDot > lastComma) {
      // "1,500.50" → dot is decimal, comma is thousands
      s = s.replace(/,/g, "");               // strip thousands commas
    } else {
      // "1.500,50" → comma is decimal, dot is thousands
      s = s.replace(/\./g, "");              // strip thousands dots
      s = s.replace(",", ".");               // replace decimal comma with dot
    }
  } else if (lastComma >= 0) {
    // Only comma present → treat as decimal comma (Argentine style: "1,5" → "1.5")
    // But only if it looks like a decimal (not trailing thousands like "1500,")
    if (lastComma === s.length - 1) {
      // Trailing comma: "1500," → just strip it (user typed incomplete)
      s = s.slice(0, -1);
    } else {
      s = s.replace(",", ".");
    }
  }
  // else: only dot present → already correct

  return s;
}

// ── Component ──

export default function DecimalInput({
  value,
  onChange,
  onBlur,
  disabled = false,
  className = "",
  placeholder,
  decimals = 2,
  min,
  max,
  step: _step,
  isCurrency = false,
  width = "min-w-[10ch]",
  id,
}: DecimalInputProps) {
  const [raw, setRaw] = useState("");
  const committedRef = useRef(false);

  // Sync from outside: when parent changes value and we didn't
  // trigger it ourselves, reset raw so the formatted display
  // reflects the new value.
  useEffect(() => {
    if (!committedRef.current) {
      setRaw("");
    }
    committedRef.current = false;
  }, [value, decimals, isCurrency]);

  const displayValue = raw || formatNumber(value, decimals, isCurrency);

  const handleFocus = () => {
    if (!raw) {
      setRaw(Number(value).toFixed(decimals));
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setRaw(e.target.value);
  };

  const handleBlur = () => {
    committedRef.current = true;

    let final: number;
    const trimmed = raw.trim();

    if (trimmed === "" || trimmed === "-") {
      final = min ?? 0;
    } else {
      let toParse = normalizeDecimal(trimmed);

      // Handle leading dot: ".5" → "0.5"
      if (toParse.startsWith(".")) {
        toParse = "0" + toParse;
      }
      // Handle negative with leading dot: "-.5" → "-0.5"
      if (toParse.startsWith("-.")) {
        toParse = "-0." + toParse.slice(2);
      }

      const parsed = Number(toParse);
      if (isNaN(parsed)) {
        // Invalid input (letters, etc.) — revert to last valid value
        setRaw("");
        onBlur?.();
        return;
      }

      final = parsed;
    }

    // Clamp
    if (min !== undefined && final < min) final = min;
    if (max !== undefined && final > max) final = max;

    // Round
    const factor = Math.pow(10, decimals);
    final = Math.round(final * factor) / factor;

    // Format display for the committed value
    setRaw(formatNumber(final, decimals, isCurrency));

    onChange(final);
    onBlur?.();
  };

  return (
    <input
      id={id}
      type="text"
      inputMode="decimal"
      value={displayValue}
      onFocus={handleFocus}
      onChange={handleChange}
      onBlur={handleBlur}
      disabled={disabled}
      placeholder={placeholder}
      className={`border px-2 py-1 rounded ${width} ${
        disabled ? "bg-gray-200 text-gray-400" : ""
      } ${className}`}
    />
  );
}
