/**
 * IngredienteSearchSelector — Ingredient selection modal with search filter.
 *
 * Extracted from ProductosCRUD.tsx (previously the inline IngredienteSelector
 * at lines 93-207). Adds a SearchFilter component at the top of the modal
 * to filter ingredients by name. Maintains ALL existing functionality:
 * checkbox selection, DecimalInput for quantity, unit selector filtered
 * by ingredient type, and "Max Prod." calculation via convertirCantidad.
 *
 * Props:
 *   - open: controls modal visibility
 *   - onClose: called on Cancel or backdrop click
 *   - onSelect: called on Confirm with array of selected ingredient items
 *   - allIngredientes: full ingredient list (from parent state)
 *   - unidades: measurement units (for unit dropdown)
 *   - factores: conversion factor map (for Max Prod. calculation)
 *   - selected: currently selected ingredient items (for pre-population)
 */
import { useState, useMemo, useEffect } from "react";
import type { Ingrediente } from "@/features/productos/api/ingredientes";
import { formatCurrency } from "@/shared/utils/formatCurrency";
import type { UnidadMedida } from "@/features/unidades-medida/types";
import Modal from "@/shared/components/Modal";
import DecimalInput from "@/shared/components/DecimalInput";
import SearchFilter from "@/shared/components/SearchFilter";
import { convertirCantidad } from "@/shared/utils/convertirCantidad";

// ── Types ──

export type SelectedIngredientItem = {
  id: number;
  cantidad: number;
  unidad_medida_id?: number | null;
};

export interface IngredienteSearchSelectorProps {
  open: boolean;
  onClose: () => void;
  onSelect: (items: SelectedIngredientItem[]) => void;
  allIngredientes: Ingrediente[];
  unidades: UnidadMedida[];
  factores: Record<number, number>;
  selected: SelectedIngredientItem[];
}

// ── Component ──

export default function IngredienteSearchSelector({
  open,
  onClose,
  onSelect,
  allIngredientes,
  unidades,
  factores,
  selected,
}: IngredienteSearchSelectorProps) {
  const [localSelected, setLocalSelected] = useState<SelectedIngredientItem[]>([]);
  const [search, setSearch] = useState("");

  // Re-sync local selection when modal opens (captures external changes)
  useEffect(() => {
    if (open) {
      setLocalSelected(selected);
      setSearch("");
    }
  }, [open, selected]);

  const toggleIngredient = (id: number) => {
    const ing = allIngredientes.find((i) => i.id === id);
    setLocalSelected((prev) =>
      prev.some((s) => s.id === id)
        ? prev.filter((s) => s.id !== id)
        : [
            ...prev,
            {
              id,
              cantidad: 1,
              unidad_medida_id: ing?.unidad_medida_id ?? null,
            },
          ]
    );
  };

  const handleConfirm = () => {
    onSelect(localSelected);
    onClose();
  };

  // Filter ingredients by name (case-insensitive)
  const filteredIngredientes = useMemo(() => {
    if (!search.trim()) return allIngredientes;
    const q = search.toLowerCase();
    return allIngredientes.filter((ing) =>
      ing.nombre.toLowerCase().includes(q)
    );
  }, [allIngredientes, search]);

  if (!open) return null;

  return (
    <Modal
      open={true}
      onClose={onClose}
      title="Seleccionar Ingredientes"
      maxWidth="max-w-3xl"
    >
      {/* Search filter */}
      <div className="mb-4">
        <SearchFilter
          onSearch={setSearch}
          placeholder="Filtrar ingredientes..."
        />
      </div>

      {/* Ingredient table */}
      {filteredIngredientes.length === 0 ? (
        <div className="text-center text-gray-400 text-sm py-8 border rounded mb-4">
          {search.trim()
            ? "Sin resultados"
            : "No hay ingredientes disponibles"}
        </div>
      ) : (
        <table className="w-full border-collapse border mb-4">
          <thead>
            <tr className="bg-gray-200">
              <th className="border p-2 text-left">Sel.</th>
              <th className="border p-2 text-left">Nombre</th>
              <th className="border p-2 text-left">Alerg.</th>
              <th className="border p-2 text-left">Precio</th>
              <th className="border p-2 text-left">Stock</th>
              <th className="border p-2 text-left">Cantidad</th>
              <th className="border p-2 text-left">Max Prod.</th>
            </tr>
          </thead>
          <tbody>
            {filteredIngredientes.map((ing) => {
              const sel = localSelected.find((s) => s.id === ing.id);
              return (
                <tr key={ing.id}>
                  <td className="border p-2">
                    <input
                      type="checkbox"
                      checked={!!sel}
                      onChange={() => toggleIngredient(ing.id)}
                    />
                  </td>
                  <td className="border p-2">{ing.nombre}</td>
                  <td className="border p-2">
                    {ing.es_alergeno ? "Si" : "No"}
                  </td>
                  <td className="border p-2">
                    {formatCurrency(ing.precio_actual)}
                  </td>
                  <td className="border p-2">
                    {ing.stock_actual}
                    {ing.unidad_medida_simbolo
                      ? ` ${ing.unidad_medida_simbolo}`
                      : ""}
                  </td>
                  <td className="border p-2">
                    {sel && (
                      <span className="inline-flex items-center gap-1">
                        <DecimalInput
                          value={sel.cantidad}
                          onChange={(v) => {
                            setLocalSelected((prev) =>
                              prev.map((s) =>
                                s.id === ing.id ? { ...s, cantidad: v } : s
                              )
                            );
                          }}
                          decimals={2}
                          min={0.01}
                          step={0.01}
                          width="min-w-[8ch]"
                        />
                        <select
                          value={sel.unidad_medida_id ?? ""}
                          onChange={(e) => {
                            const val = e.target.value
                              ? Number(e.target.value)
                              : null;
                            setLocalSelected((prev) =>
                              prev.map((s) =>
                                s.id === ing.id
                                  ? { ...s, unidad_medida_id: val }
                                  : s
                              )
                            );
                          }}
                          className="border px-1 py-1 rounded text-xs"
                        >
                          <option value="">unidad/es</option>
                          {unidades
                            .filter((u) => {
                              const ingUnidad = unidades.find(
                                (un) => un.id === ing.unidad_medida_id
                              );
                              return (
                                !ingUnidad || u.tipo === ingUnidad.tipo
                              );
                            })
                            .map((u) => (
                              <option key={u.id} value={u.id}>
                                {u.simbolo}
                              </option>
                            ))}
                        </select>
                      </span>
                    )}
                  </td>
                  <td className="border p-2">
                    {sel
                      ? Math.floor(
                          ing.stock_actual /
                            convertirCantidad(
                              sel.cantidad,
                              sel.unidad_medida_id ??
                                ing.unidad_medida_id ??
                                null,
                              ing.unidad_medida_id ?? null,
                              factores
                            )
                        )
                      : "-"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleConfirm}
          className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer"
        >
          Confirmar
        </button>
        <button
          onClick={onClose}
          className="bg-gray-400 text-white px-4 py-1 rounded cursor-pointer"
        >
          Cancelar
        </button>
      </div>
    </Modal>
  );
}
