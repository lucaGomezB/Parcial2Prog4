/**
 * ActionButton — Shared Edit and Delete button components.
 *
 * Provides consistent styling for the two most common table-row actions
 * across all CRUD pages.
 *
 * Usage:
 *   <EditButton onClick={() => handleEdit(item)} />
 *   <EditButton onClick={() => handleEdit(item)} label="Modificar" />
 *   <DeleteButton onClick={() => handleDelete(item.id)} />
 */
import type { ReactNode } from "react";

interface ActionButtonBaseProps {
  /** Click handler. */
  onClick: () => void;
  /** Optional button label. Defaults vary by variant. */
  label?: string;
  /** Optional additional CSS classes appended to the base classes. */
  className?: string;
  /** Whether the button is disabled. */
  disabled?: boolean;
}

// ── EditButton ──

export function EditButton({ onClick, label = "Editar", className = "", disabled = false }: ActionButtonBaseProps): ReactNode {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`bg-yellow-500 text-white px-2 py-1 rounded text-xs cursor-pointer hover:bg-yellow-600 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
    >
      {label}
    </button>
  );
}

// ── DeleteButton ──

export function DeleteButton({ onClick, label = "Eliminar", className = "", disabled = false }: ActionButtonBaseProps): ReactNode {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`bg-red-600 text-white px-2 py-1 rounded text-xs cursor-pointer hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
    >
      {label}
    </button>
  );
}
