/**
 * CategoriaTreeSelector — Hierarchical category tree selector modal.
 *
 * Replaces the flat category table in the product create/edit form with
 * a collapsible tree view. Fetches the full category tree from the API
 * and renders it recursively using <div> elements (not table rows).
 *
 * Features:
 *   - Recursive tree rendering with indentation by depth
 *   - Expand/collapse toggle (+/-) for parent nodes
 *   - Independent checkboxes per node (selecting parent does NOT select children)
 *   - Search/filter with 300ms debounce, preserving ancestor nodes
 *   - Auto-expand all matching nodes when search is active
 *   - "Sin resultados" message when filter yields empty
 *   - Confirm/Cancel buttons
 *
 * Props:
 *   - open: controls modal visibility
 *   - onClose: called on Cancel or backdrop click
 *   - onSelect: called on Confirm with the array of selected category IDs
 *   - selectedIds: currently selected category IDs (for pre-selection on edit)
 */
import { useState, useEffect, useMemo } from "react";
import { categoriasApi, type CategoriaTree } from "@/features/categorias/api/categorias";
import { useDebounce } from "@/shared/hooks/useDebounce";
import Modal from "@/shared/components/Modal";

// ── Props ──

export interface CategoriaTreeSelectorProps {
  open: boolean;
  onClose: () => void;
  onSelect: (categoriaIds: number[]) => void;
  selectedIds: number[];
}

// ── Helpers ──

/**
 * Recursively filters the tree by name (case-insensitive).
 * Preserves ancestor nodes when descendants match so the user
 * sees the full hierarchical path.
 */
function filterTree(nodes: CategoriaTree[], query: string): CategoriaTree[] {
  if (!query.trim()) return nodes;
  const q = query.toLowerCase();

  function matches(node: CategoriaTree): boolean {
    return node.nombre.toLowerCase().includes(q);
  }

  function filterRecursive(list: CategoriaTree[]): CategoriaTree[] {
    const result: CategoriaTree[] = [];
    for (const node of list) {
      const filteredChildren = filterRecursive(node.subcategorias);
      const selfMatches = matches(node);
      const childrenMatch = filteredChildren.length > 0;
      if (selfMatches || childrenMatch) {
        result.push({
          ...node,
          subcategorias: selfMatches ? node.subcategorias : filteredChildren,
        });
      }
    }
    return result;
  }

  return filterRecursive(nodes);
}

/** Collects all node IDs from a tree (used for auto-expand on search). */
function collectAllIds(nodes: CategoriaTree[]): number[] {
  const ids: number[] = [];
  for (const node of nodes) {
    ids.push(node.id);
    if (node.subcategorias.length > 0) {
      ids.push(...collectAllIds(node.subcategorias));
    }
  }
  return ids;
}

// ── Recursive tree node component ──

function TreeNode({
  node,
  depth,
  expanded,
  onToggle,
  selectedIds,
  onToggleSelect,
}: {
  node: CategoriaTree;
  depth: number;
  expanded: Set<number>;
  onToggle: (id: number) => void;
  selectedIds: number[];
  onToggleSelect: (id: number) => void;
}) {
  const hasChildren = node.subcategorias.length > 0;
  const isExpanded = expanded.has(node.id);

  const rows: React.ReactNode[] = [];

  // Current node
  rows.push(
    <div
      key={node.id}
      className="flex items-center gap-1.5 py-1.5 hover:bg-blue-50 transition-colors"
      style={{ paddingLeft: `${12 + depth * 24}px`, paddingRight: "12px" }}
    >
      {/* Toggle button or spacer */}
      {hasChildren ? (
        <button
          type="button"
          onClick={() => onToggle(node.id)}
          className="min-w-[24px] min-h-[24px] w-6 h-6 flex items-center justify-center rounded text-sm font-bold border border-gray-300 bg-white hover:bg-gray-100 cursor-pointer transition-colors select-none leading-none"
          aria-label={isExpanded ? "Colapsar" : "Expandir"}
        >
          {isExpanded ? "\u2212" : "+"}
        </button>
      ) : (
        <span className="inline-block w-6" />
      )}

      {/* Checkbox */}
      <input
        type="checkbox"
        checked={selectedIds.includes(node.id)}
        onChange={() => onToggleSelect(node.id)}
        className="cursor-pointer"
      />

      {/* Category name */}
      <span className="font-medium text-gray-900 text-sm">{node.nombre}</span>

      {/* Child count badge */}
      {hasChildren && (
        <span className="text-xs text-gray-400 ml-0.5">
          ({node.subcategorias.length})
        </span>
      )}
    </div>
  );

  // Recursive children (if expanded)
  if (hasChildren && isExpanded) {
    for (const child of node.subcategorias) {
      rows.push(
        <TreeNode
          key={child.id}
          node={child}
          depth={depth + 1}
          expanded={expanded}
          onToggle={onToggle}
          selectedIds={selectedIds}
          onToggleSelect={onToggleSelect}
        />
      );
    }
  }

  return <>{rows}</>;
}

// ── Main component ──

export default function CategoriaTreeSelector({
  open,
  onClose,
  onSelect,
  selectedIds,
}: CategoriaTreeSelectorProps) {
  const [treeData, setTreeData] = useState<CategoriaTree[]>([]);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [localSelected, setLocalSelected] = useState<number[]>([]);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 300);

  // Fetch tree data on mount
  useEffect(() => {
    categoriasApi.getTree().then(setTreeData).catch(() => {});
  }, []);

  // Sync local selection when modal opens or selectedIds change
  useEffect(() => {
    if (open) {
      setLocalSelected(selectedIds);
    }
  }, [open, selectedIds]);

  // Auto-expand all matching nodes when a search filter is active
  useEffect(() => {
    if (debouncedSearch.trim()) {
      const filtered = filterTree(treeData, debouncedSearch);
      const allIds = collectAllIds(filtered);
      setExpanded(new Set(allIds));
    } else {
      setExpanded(new Set());
    }
  }, [debouncedSearch, treeData]);

  const toggleExpand = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleSelect = (id: number) => {
    setLocalSelected((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const filteredTree = useMemo(
    () => filterTree(treeData, debouncedSearch),
    [treeData, debouncedSearch]
  );

  const handleConfirm = () => {
    onSelect(localSelected);
    onClose();
  };

  if (!open) return null;

  return (
    <Modal open={true} onClose={onClose} title="Seleccionar Categorias" maxWidth="max-w-2xl">
      {/* Search input */}
      <div className="mb-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filtrar categorias..."
          className="border border-gray-300 rounded px-3 py-1.5 text-sm w-full focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* Tree container */}
      <div className="max-h-[50vh] overflow-y-auto border rounded mb-4">
        {filteredTree.length === 0 ? (
          <div className="p-4 text-center text-gray-400 text-sm">
            {debouncedSearch.trim()
              ? "Sin resultados"
              : "No hay categorias"}
          </div>
        ) : (
          filteredTree.map((node) => (
            <TreeNode
              key={node.id}
              node={node}
              depth={0}
              expanded={expanded}
              onToggle={toggleExpand}
              selectedIds={localSelected}
              onToggleSelect={toggleSelect}
            />
          ))
        )}
      </div>

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
