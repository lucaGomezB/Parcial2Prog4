/**
 * CategoriasCRUD — Category management admin page.
 *
 * Features:
 *   - Hierarchical tree display (parent-child relationships via subcategorias).
 *   - Expand/collapse tree nodes.
 *   - CRUD operations: create, edit, delete categories.
 *   - Parent category selection via a tree-based modal (prevents cycles).
 *   - Text filter that recursively filters the tree.
 *   - Excel export of the flattened (depth-annotated) tree.
 *
 * The category tree is fetched once from categoriasApi.getTree() and
 * filtering is done client-side via filterTree().
 */

import { useEffect, useState, useCallback, useRef } from "react";
import type { CategoriaCreate, CategoriaTree } from "../api/categorias";
import { categoriasApi } from "../api/categorias";
import { exportToExcel } from "../utils/exportExcel";
import { useAppForm, required } from "../hooks/useAppForm";


/* ── Helpers ── */

/**
 * Recursively flattens a tree of CategoriaTree nodes into a linear array,
 * annotating each node with its nesting `depth` for display/export.
 */
function flattenTree(nodes: CategoriaTree[], depth = 0): (CategoriaTree & { depth: number })[] {
  const result: (CategoriaTree & { depth: number })[] = [];
  for (const node of nodes) {
    result.push({ ...node, depth });
    if (node.subcategorias.length > 0) {
      result.push(...flattenTree(node.subcategorias, depth + 1));
    }
  }
  return result;
}

/**
 * Recursively filters a category tree by name (case-insensitive).
 * If a parent matches, all its children are kept; if only children match,
 * only those children are included (parent omitted to avoid false positives).
 */
function filterTree(nodes: CategoriaTree[], query: string): CategoriaTree[] {
  const lower = query.toLowerCase();
  return nodes.reduce<CategoriaTree[]>((acc, node) => {
    const matches = node.nombre.toLowerCase().includes(lower);
    const filteredChildren = filterTree(node.subcategorias, query);
    if (matches || filteredChildren.length > 0) {
      acc.push({
        ...node,
        subcategorias: matches ? node.subcategorias : filteredChildren,
      });
    }
    return acc;
  }, []);
}

/**
 * Collects all descendant IDs (including self) for a given node.
 * Used to exclude self + descendants from the parent selector to prevent cycles.
 */
function getDescendantIds(node: CategoriaTree): number[] {
  const ids: number[] = [node.id];
  for (const child of node.subcategorias) {
    ids.push(...getDescendantIds(child));
  }
  return ids;
}

/**
 * Recursively finds a category node by ID within the tree.
 */
function findCategoriaInTree(nodes: CategoriaTree[], id: number): CategoriaTree | null {
  for (const node of nodes) {
    if (node.id === id) return node;
    if (node.subcategorias.length > 0) {
      const found = findCategoriaInTree(node.subcategorias, id);
      if (found) return found;
    }
  }
  return null;
}

/* ── Tree Row ── */

/**
 * A single row in the category tree table.
 * Supports recursive rendering of children when expanded.
 *
 * Indentation is computed from `depth` via inline `paddingLeft` style.
 */
function CategoryTreeRow({
  categoria, depth, expanded, onToggle, onEdit, onDelete,
}: {
  categoria: CategoriaTree;
  depth: number;
  expanded: Set<number>;
  onToggle: (id: number) => void;
  onEdit: (cat: CategoriaTree) => void;
  onDelete: (id: number) => void;
}) {
  const hasChildren = categoria.subcategorias.length > 0;
  const isExpanded = expanded.has(categoria.id);

  return (
    <>
      <tr className="hover:bg-gray-100 border-b">
        <td className="p-2" style={{ paddingLeft: `${12 + depth * 24}px` }}>
          <span className="inline-flex items-center gap-1">
            {hasChildren ? (
              <button
                onClick={() => onToggle(categoria.id)}
                className="border border-gray-400 bg-white text-gray-700 hover:bg-gray-100 text-xs w-5 h-5 flex items-center justify-center rounded-sm cursor-pointer select-none"
                title={isExpanded ? "Collapse" : "Expand"}
              >
                {isExpanded ? "-" : "+"}
              </button>
            ) : (
              // Spacer to align items without children with those that have expand buttons
              <span className="w-5 h-5 inline-block" />
            )}
            <span className="font-semibold text-gray-900">{categoria.nombre}</span>
          </span>
        </td>
        <td className="p-2 text-sm text-gray-600">{categoria.descripcion ?? "-"}</td>
        <td className="p-2">
          <div className="flex gap-1">
            <button onClick={() => onEdit(categoria)}
              className="bg-yellow-500 text-white px-2 py-1 rounded text-xs cursor-pointer hover:bg-yellow-600">Editar</button>
            <button onClick={() => onDelete(categoria.id)}
              className="bg-red-600 text-white px-2 py-1 rounded text-xs cursor-pointer hover:bg-red-700">Eliminar</button>
          </div>
        </td>
      </tr>
      {/* Recursively render children if expanded */}
      {hasChildren && isExpanded && (
        categoria.subcategorias.map((child) => (
          <CategoryTreeRow
            key={child.id}
            categoria={child}
            depth={depth + 1}
            expanded={expanded}
            onToggle={onToggle}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        ))
      )}
    </>
  );
}

/* ── Selector de Categoria Padre (jerarquico) ── */

/**
 * Modal for selecting a parent category (hierarchical picker).
 * Excludes self and all descendants to prevent circular references.
 *
 * The `excludeIds` set is built by walking the tree from the current node
 * downwards (getDescendantIds) — this prevents selecting a descendant as parent.
 */
function ParentSelector({ treeData, currentId, onSelect, onClose }: {
  treeData: CategoriaTree[]; currentId: number | null; onSelect: (id: number | null, name: string) => void; onClose: () => void;
}) {
  // Build a set of IDs to exclude (self + descendants)
  const excludeIds = new Set<number>();
  if (currentId !== null) {
    const findNode = (nodes: CategoriaTree[]): CategoriaTree | null => {
      for (const n of nodes) {
        if (n.id === currentId) return n;
        const found = findNode(n.subcategorias);
        if (found) return found;
      }
      return null;
    };
    const self = findNode(treeData);
    if (self) {
      for (const id of getDescendantIds(self)) excludeIds.add(id);
    }
  }

  const renderTreeOptions = (nodes: CategoriaTree[], depth = 0): React.ReactNode[] => {
    const elements: React.ReactNode[] = [];
    for (const node of nodes) {
      if (excludeIds.has(node.id)) continue;
      elements.push(
        <tr key={node.id} className="hover:bg-gray-100">
          <td className="p-2" style={{ paddingLeft: `${12 + depth * 20}px` }}>
            <span className="font-semibold text-gray-900">{node.nombre}</span>
          </td>
          <td className="p-2 text-sm text-gray-600">{node.descripcion ?? "-"}</td>
          <td className="p-2">
            <button onClick={() => onSelect(node.id, node.nombre)}
              className="bg-blue-600 text-white px-2 py-1 rounded text-xs cursor-pointer hover:bg-blue-700">Seleccionar</button>
          </td>
        </tr>
      );
      if (node.subcategorias.length > 0) {
        elements.push(...renderTreeOptions(node.subcategorias, depth + 1));
      }
    }
    return elements;
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-md max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Seleccionar Categoria Padre</h2>
          <button onClick={onClose} className="text-gray-500 text-xl cursor-pointer">X</button>
        </div>
        {/* Option to make this a root category (no parent) */}
        <button onClick={() => onSelect(null, "")}
          className="mb-4 bg-gray-600 text-white px-4 py-1 rounded cursor-pointer hover:bg-gray-700">Sin Padre</button>
        <table className="w-full border-collapse border">
          <thead><tr className="bg-gray-200">
            <th className="border p-2 text-left">Nombre</th>
            <th className="border p-2 text-left">Descripcion</th>
            <th className="border p-2 text-left">Accion</th>
          </tr></thead>
          <tbody>{renderTreeOptions(treeData)}</tbody>
        </table>
      </div>
    </div>
  );
}

/* ── Main Page ── */

/**
 * CategoriasCRUD page component.
 *
 * State:
 *   - treeData: the full hierarchical category tree from the backend.
 *   - expanded: Set<number> of node IDs that are currently expanded.
 *   - filter: text filter applied client-side.
 *   - showForm/editingId: control the create/edit inline form.
 *   - selectedParentName: display text for the chosen parent category.
 */
export default function CategoriasCRUD() {
  const [treeData, setTreeData] = useState<CategoriaTree[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [selectedParentName, setSelectedParentName] = useState("");

  /**
   * TanStack Form for creating/editing a single category.
   * Switching between create and edit is handled by reset() with different defaults.
   */
  const form = useAppForm<CategoriaCreate>({
    defaultValues: { nombre: "", descripcion: "", parent_id: null, orden_display: 0 },
    onSubmit: async ({ value }) => {
      try {
        if (editingId) {
          await categoriasApi.update(editingId, value);
        } else {
          await categoriasApi.create(value);
        }
        handleCloseForm();
        loadTree();
      } catch (err) {
        setError((err as Error).message);
      }
    },
  });
  const [showParentSelector, setShowParentSelector] = useState(false);

  const formRef = useRef<HTMLFormElement>(null);

  // Scroll the form into view when it opens (useful on mobile)
  useEffect(() => {
    if (showForm) formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [showForm]);

  /** Fetches the full category tree from the backend. */
  const loadTree = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await categoriasApi.getTree();
      setTreeData(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadTree(); }, [loadTree]);

  /** Toggle expansion state for a tree node. */
  const toggleExpand = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  /**
   * Opens the form in edit mode, pre-fills with the category's current values,
   * and resolves the parent category name from the tree for display.
   */
  const handleEdit = (cat: CategoriaTree) => {
    setEditingId(cat.id);
    setShowForm(true);
    form.reset({
      nombre: cat.nombre,
      descripcion: cat.descripcion ?? "",
      parent_id: cat.parent_id,
      orden_display: cat.orden_display,
    });
    // Find parent name from tree
    const findParent = (nodes: CategoriaTree[]): string => {
      for (const n of nodes) {
        if (n.id === cat.parent_id) return n.nombre;
        const found = findParent(n.subcategorias);
        if (found) return found;
      }
      return "";
    };
    setSelectedParentName(cat.parent_id !== null ? findParent(treeData) : "");
    setShowParentSelector(false);
  };

  /** Opens the form in create mode with blank defaults. */
  const handleCreate = () => {
    setEditingId(null);
    setShowForm(true);
    form.reset({ nombre: "", descripcion: "", parent_id: null, orden_display: 0 });
    setSelectedParentName("");
    setShowParentSelector(false);
  };

  /** Closes the form and resets all editing state. */
  const handleCloseForm = () => {
    setShowForm(false);
    setEditingId(null);
    form.reset({ nombre: "", descripcion: "", parent_id: null, orden_display: 0 });
    setSelectedParentName("");
  };

  /** Deletes a category after user confirmation. */
  const handleDelete = async (id: number) => {
    if (!confirm("Eliminar esta categoria?")) return;
    try {
      await categoriasApi.delete(id);
      loadTree();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  // Apply filter to tree (client-side recursive filter)
  const displayTree = filter ? filterTree(treeData, filter) : treeData;

  // Flat list for Excel export
  const flatForExport = flattenTree(displayTree);

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Categorias</h1>
      {error && <div className="bg-red-100 text-red-700 p-2 mb-4 rounded">{error}</div>}

      {/* Toolbar: filter input + action buttons */}
      <div className="flex gap-2 mb-4 flex-wrap items-center">
        <input type="text" placeholder="Filtrar por nombre..." value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="border px-3 py-1 rounded" />

        <button onClick={handleCreate}
          className="bg-green-600 text-white px-4 py-1.5 rounded cursor-pointer hover:bg-green-700">+ Nueva</button>
        <button onClick={() => exportToExcel(flatForExport.map(({ id, nombre, descripcion, parent_id, orden_display, depth }) => ({
              id, nombre, descripcion: descripcion ?? "", parent_id: parent_id ?? "", orden_display, profundidad: depth,
            })), "categorias")}
          className="bg-blue-600 text-white px-4 py-1.5 rounded cursor-pointer hover:bg-blue-700">Exportar Excel</button>
      </div>

      {/* Inline create/edit form — shown/hidden via showForm state */}
      {showForm && (
        <form ref={formRef} onSubmit={(e) => { e.preventDefault(); e.stopPropagation(); void form.handleSubmit(); }} className="border p-4 mb-4 rounded bg-gray-50 grid grid-cols-2 gap-2">
          <div>
            <label className="block text-sm font-medium">Nombre</label>
            <form.Field name="nombre" validators={{ onChange: required() }}>
              {(field) => (
                <input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  className="border px-2 py-1 rounded w-full"
                />
              )}
            </form.Field>
          </div>
          <div>
            <label className="block text-sm font-medium">Descripcion</label>
            <form.Field name="descripcion">
              {(field) => (
                <input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  className="border px-2 py-1 rounded w-full"
                />
              )}
            </form.Field>
          </div>
          {/* Parent category selector — opens a tree-based modal */}
          <div>
            <label className="block text-sm font-medium">Es una subcategoria de:</label>
            <div className="flex gap-2">
              <input value={selectedParentName} readOnly className="border px-2 py-1 rounded flex-1" placeholder="Sin padre" />
              <button type="button" onClick={() => setShowParentSelector(true)}
                className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer hover:bg-blue-700">Seleccionar</button>
            </div>
          </div>


          <div className="col-span-2 flex gap-2 mt-2">
            <button type="submit" className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer hover:bg-blue-700">
              {editingId ? "Actualizar" : "Crear"}</button>
            <button type="button" onClick={handleCloseForm}
              className="bg-gray-400 text-white px-4 py-1 rounded cursor-pointer hover:bg-gray-500">Cancelar</button>
          </div>
        </form>
      )}

      {/* Parent selector modal */}
      {showParentSelector && (
        <ParentSelector
          treeData={treeData}
          currentId={editingId}
          onSelect={(id, name) => {
            form.setFieldValue('parent_id', id);
            setSelectedParentName(name);
            setShowParentSelector(false);
          }}
          onClose={() => setShowParentSelector(false)}
        />
      )}

      {/* Loading / tabular tree display */}
      {loading ? (
        <p className="text-gray-500">Cargando...</p>
      ) : (
        <table className="w-full border-collapse border">
          <thead><tr className="bg-gray-200">
            <th className="border p-2 text-left">Nombre</th>
            <th className="border p-2 text-left">Descripcion</th>
            <th className="border p-2 text-left">Acciones</th>
          </tr></thead>
          <tbody>
            {displayTree.length === 0 ? (
              <tr><td colSpan={3} className="border p-2 text-center text-gray-500">Sin resultados</td></tr>
            ) : (
              displayTree.map((root) => (
                <CategoryTreeRow
                  key={root.id}
                  categoria={root}
                  depth={0}
                  expanded={expanded}
                  onToggle={toggleExpand}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                />
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
