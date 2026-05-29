import { useEffect, useState, useCallback } from "react";
import type { Categoria, CategoriaCreate, CategoriaTree } from "../api/categorias";
import { categoriasApi } from "../api/categorias";
import { exportToExcel } from "../utils/exportExcel";

/* ── Helpers ── */

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

function getDescendantIds(node: CategoriaTree): number[] {
  const ids: number[] = [node.id];
  for (const child of node.subcategorias) {
    ids.push(...getDescendantIds(child));
  }
  return ids;
}

/* ── Tree Row ── */
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
                title={isExpanded ? "Colapsar" : "Expandir"}
              >
                {isExpanded ? "−" : "+"}
              </button>
            ) : (
              <span className="w-5 h-5 inline-block" />
            )}
            <span className="font-semibold text-gray-900">{categoria.nombre}</span>
          </span>
        </td>
        <td className="p-2 text-sm text-gray-600">{categoria.descripcion ?? "-"}</td>
        <td className="p-2">
          {categoria.es_primordial ? (
            <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">Primordial</span>
          ) : (
            <span className="text-sm text-gray-400">-</span>
          )}
        </td>
        <td className="p-2">
          <div className="flex gap-1">
            <button onClick={() => onEdit(categoria)}
              className="bg-yellow-500 text-white px-2 py-1 rounded text-xs cursor-pointer hover:bg-yellow-600">Editar</button>
            <button onClick={() => onDelete(categoria.id)}
              className="bg-red-600 text-white px-2 py-1 rounded text-xs cursor-pointer hover:bg-red-700">Eliminar</button>
          </div>
        </td>
      </tr>
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

/* ── Selector de Categoría Padre (jerárquico) ── */
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
          <h2 className="text-lg font-bold">Seleccionar Categoría Padre</h2>
          <button onClick={onClose} className="text-gray-500 text-xl cursor-pointer">✕</button>
        </div>
        <button onClick={() => onSelect(null, "")}
          className="mb-4 bg-gray-600 text-white px-4 py-1 rounded cursor-pointer hover:bg-gray-700">Sin Padre</button>
        <table className="w-full border-collapse border">
          <thead><tr className="bg-gray-200">
            <th className="border p-2 text-left">Nombre</th>
            <th className="border p-2 text-left">Descripción</th>
            <th className="border p-2 text-left">Acción</th>
          </tr></thead>
          <tbody>{renderTreeOptions(treeData)}</tbody>
        </table>
      </div>
    </div>
  );
}

/* ── Main Page ── */
export default function CategoriasCRUD() {
  const [treeData, setTreeData] = useState<CategoriaTree[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CategoriaCreate>({
    nombre: "", descripcion: "", parent_id: null, orden_display: 0, es_primordial: false,
  });
  const [selectedParentId, setSelectedParentId] = useState<number | null>(null);
  const [selectedParentName, setSelectedParentName] = useState("");
  const [showParentSelector, setShowParentSelector] = useState(false);

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

  const toggleExpand = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleEdit = (cat: CategoriaTree) => {
    setEditingId(cat.id);
    setShowForm(true);
    setForm({
      nombre: cat.nombre,
      descripcion: cat.descripcion ?? "",
      parent_id: cat.parent_id,
      orden_display: cat.orden_display,
      es_primordial: cat.es_primordial,
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
    setSelectedParentId(cat.parent_id);
    setSelectedParentName(cat.parent_id !== null ? findParent(treeData) : "");
    setShowParentSelector(false);
  };

  const handleCreate = () => {
    setEditingId(null);
    setShowForm(true);
    setForm({ nombre: "", descripcion: "", parent_id: null, orden_display: 0, es_primordial: false });
    setSelectedParentId(null);
    setSelectedParentName("");
    setShowParentSelector(false);
  };

  const handleCloseForm = () => {
    setShowForm(false);
    setEditingId(null);
    setForm({ nombre: "", descripcion: "", parent_id: null, orden_display: 0, es_primordial: false });
    setSelectedParentId(null);
    setSelectedParentName("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await categoriasApi.update(editingId, form);
      } else {
        await categoriasApi.create(form);
      }
      handleCloseForm();
      loadTree();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("¿Eliminar esta categoría?")) return;
    try {
      await categoriasApi.delete(id);
      loadTree();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  // Apply filter to tree
  const displayTree = filter ? filterTree(treeData, filter) : treeData;

  // Flat list for Excel export
  const flatForExport = flattenTree(displayTree);

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Categorías</h1>
      {error && <div className="bg-red-100 text-red-700 p-2 mb-4 rounded">{error}</div>}

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

      {showForm && (
        <form onSubmit={handleSubmit} className="border p-4 mb-4 rounded bg-gray-50 grid grid-cols-2 gap-2">
          <div>
            <label className="block text-sm font-medium">Nombre</label>
            <input value={form.nombre}
              onChange={(e) => setForm({ ...form, nombre: e.target.value })}
              className="border px-2 py-1 rounded w-full" required />
          </div>
          <div>
            <label className="block text-sm font-medium">Descripción</label>
            <input value={form.descripcion ?? ""}
              onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
              className="border px-2 py-1 rounded w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium">Categoría Padre</label>
            <div className="flex gap-2">
              <input value={selectedParentName} readOnly className="border px-2 py-1 rounded flex-1" placeholder="Sin padre" />
              <button type="button" onClick={() => setShowParentSelector(true)}
                className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer hover:bg-blue-700">Seleccionar</button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium">Orden Display</label>
            <input type="number" value={form.orden_display ?? 0}
              onChange={(e) => setForm({ ...form, orden_display: Number(e.target.value) })}
              className="border px-2 py-1 rounded w-full" />
          </div>
          <div className="col-span-2 flex items-center gap-2">
            <label className="text-sm font-medium">Es primordial</label>
            <input type="checkbox" checked={form.es_primordial ?? false}
              onChange={(e) => setForm({ ...form, es_primordial: e.target.checked })}
              className="w-4 h-4 cursor-pointer" />
          </div>
          <div className="col-span-2 flex gap-2 mt-2">
            <button type="submit" className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer hover:bg-blue-700">
              {editingId ? "Actualizar" : "Crear"}</button>
            <button type="button" onClick={handleCloseForm}
              className="bg-gray-400 text-white px-4 py-1 rounded cursor-pointer hover:bg-gray-500">Cancelar</button>
          </div>
        </form>
      )}

      {showParentSelector && (
        <ParentSelector
          treeData={treeData}
          currentId={editingId}
          onSelect={(id, name) => {
            setSelectedParentId(id);
            setSelectedParentName(name);
            setShowParentSelector(false);
            setForm((f) => ({ ...f, parent_id: id }));
          }}
          onClose={() => setShowParentSelector(false)}
        />
      )}

      {loading ? (
        <p className="text-gray-500">Cargando...</p>
      ) : (
        <table className="w-full border-collapse border">
          <thead><tr className="bg-gray-200">
            <th className="border p-2 text-left">Nombre</th>
            <th className="border p-2 text-left">Descripción</th>
            <th className="border p-2 text-left">Primordial</th>
            <th className="border p-2 text-left">Acciones</th>
          </tr></thead>
          <tbody>
            {displayTree.length === 0 ? (
              <tr><td colSpan={4} className="border p-2 text-center text-gray-500">Sin resultados</td></tr>
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
