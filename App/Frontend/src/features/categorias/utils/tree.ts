/**
 * Category tree utility functions.
 *
 * Extracted from CategoriasCRUD.tsx for reuse across features.
 * Works with the CategoriaTree recursive type from the categorias API.
 */
import type { CategoriaTree } from "@/features/categorias/api/categorias";

/**
 * Returns all descendant category IDs including the node itself.
 * Recursively traverses subcategorias to collect all IDs in the subtree.
 *
 * Used for category-based product filtering: when a user selects
 * a category, products in ALL descendant subcategories are shown.
 */
export function getDescendantIds(node: CategoriaTree): number[] {
  const ids: number[] = [node.id];
  for (const child of node.subcategorias) {
    ids.push(...getDescendantIds(child));
  }
  return ids;
}
