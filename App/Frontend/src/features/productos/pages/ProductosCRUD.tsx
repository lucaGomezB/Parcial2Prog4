/**
 * ProductosCRUD — Product management page with role-based views.
 *
 * Roles and what they see:
 *   - admin:   full CRUD + category/ingredient management + variant bulk creation.
 *   - stock:   stock-only editing (quantity, availability toggle).
 *   - pedidos: full view but no create/delete (mid-level access).
 *   - client:  read-only menu view with "Agregar al carrito" button.
 *
 * State management: TanStack Query for products, TanStack Form for create/edit.
 * Uses DataTable with server-side pagination.
 */
import { useEffect, useMemo, useState, useRef } from "react";
import { useStore } from "@tanstack/react-form";
import { useAppForm, required } from "@/shared/hooks/useAppForm";
import type { Producto, ProductoFormValues } from "@/features/productos/api/productos";
import { productosApi } from "@/features/productos/api/productos";
import type { Ingrediente } from "@/features/productos/api/ingredientes";
import { ingredientesApi } from "@/features/productos/api/ingredientes";
import type { CategoriaTree } from "@/features/categorias/api/categorias";
import { categoriasApi } from "@/features/categorias/api/categorias";
import { unidadesMedidaApi } from "@/features/unidades-medida/api/unidadesMedidaApi";
import type { UnidadMedida, UnidadMedidaTipo } from "@/features/unidades-medida/types";
import { useProductos, useCreateProducto, useUpdateProducto, useDeleteProducto } from "@/features/productos/hooks/useProductos";
import { useAdminProductoWebSocket } from "@/features/productos/hooks/useAdminProductoWebSocket";
import { getAccessToken, getUserRoles } from "@/shared/api/client";
import ImageCarousel from "@/shared/components/ImageCarousel";
import { addToast } from "@/shared/components/Toast";
import DataTable, { type DataTableColumn } from "@/shared/components/DataTable";
import { useNavigate } from "react-router-dom";
import { exportToExcel } from "@/shared/utils/exportExcel";
import { parseApiError } from "@/shared/utils/apiErrors";
import { useCartStore } from "@/shared/store/cartStore";
import { isAxiosError } from "axios";

import { STOCK_EXCEEDED_MESSAGE } from "@/shared/constants/cartMessages";
import CrudToolbar from "@/shared/components/CrudToolbar";
import ConfirmDialog from "@/shared/components/ConfirmDialog";
import Modal from "@/shared/components/Modal";
import { useCrudTable } from "@/shared/hooks/useCrudTable";
import { useDebounce } from "@/shared/hooks/useDebounce";
import ErrorBanner from "@/shared/components/ErrorBanner";
import { EditButton, DeleteButton } from "@/shared/components/ActionButton";
import FormFooter from "@/shared/components/FormFooter";
import { useCloudinaryUpload } from "@/shared/hooks/useCloudinaryUpload";
import DecimalInput from "@/shared/components/DecimalInput";
import { formatCurrency } from "@/shared/utils/formatCurrency";
import { convertirCantidad } from "@/shared/utils/convertirCantidad";
import CategoriaTreeSelector from "@/features/productos/components/CategoriaTreeSelector";
import IngredienteSearchSelector from "@/features/productos/components/IngredienteSearchSelector";

const DEFAULT_LIMIT = 10;

/* ── Helpers ── */

/** Finds category nodes in the tree by ID, returning display-friendly objects. */
function findCategoriesInTree(
  nodes: CategoriaTree[],
  ids: number[]
): { id: number; nombre: string; descripcion: string | null }[] {
  const result: { id: number; nombre: string; descripcion: string | null }[] = [];
  const idSet = new Set(ids);

  function search(list: CategoriaTree[]) {
    for (const node of list) {
      if (idSet.has(node.id)) {
        result.push({ id: node.id, nombre: node.nombre, descripcion: node.descripcion });
        if (result.length === ids.length) return;
      }
      if (node.subcategorias.length > 0) {
        search(node.subcategorias);
      }
    }
  }

  search(nodes);
  return result;
}

/* ── Pagina principal ── */

export default function ProductosCRUD({ role = 'admin' }: { role?: 'admin' | 'stock' | 'pedidos' | 'client' }) {
  const navigate = useNavigate();
  const readOnly = role === 'client';
  const isStockMode = role === 'stock';
  const hideCreate = role !== 'admin';
  const hideDelete = role === 'client' || role === 'stock';
  const hideExport = role === 'client' || role === 'stock';

  // ── UI-only state ──
  const crud = useCrudTable({ defaultLimit: DEFAULT_LIMIT, defaultSortBy: 'id', defaultSortOrder: 'desc' });
  const { search, setSearch, sortBy, sortOrder, skip, limit, handlePageChange, handleLimitChange } = crud;
  const debouncedSearch = useDebounce(search, 300);

  const handleSort = (newSortBy: string, newSortOrder: "asc" | "desc") => {
    crud.handleSort(newSortBy, newSortOrder);
    handlePageChange(0);
  };

  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [stockEditOnly, setStockEditOnly] = useState(false);
  const [selectedCategorias, setSelectedCategorias] = useState<{id: number, nombre: string, descripcion: string | null}[]>([]);
  const [selectedIngredientes, setSelectedIngredientes] = useState<{id: number, nombre: string, es_alergeno: boolean, cantidad: number, unidad_medida_id?: number | null, es_removible: boolean}[]>([]);
  const [showCategoriaSelector, setShowCategoriaSelector] = useState(false);
  const [showIngredienteSelector, setShowIngredienteSelector] = useState(false);
  const [showStockDetail, setShowStockDetail] = useState<Producto | null>(null);
  const [stockDetailData, setStockDetailData] = useState<import("@/features/productos/api/productos").IngredienteStockDetail[]>([]);
  const [stockDetailLoading, setStockDetailLoading] = useState(false);
  const [recentlyAdded, setRecentlyAdded] = useState<Set<number>>(new Set());
  const addTimerRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  // ── Delete confirmation dialog state (from useCrudTable) ──

  // ── Inline "Nueva unidad de medida" form ──
  const [showNewUnidadForm, setShowNewUnidadForm] = useState(false);
  const [newUnidad, setNewUnidad] = useState({ nombre: '', simbolo: '', tipo: 'unidad' as UnidadMedidaTipo, factor_conversion: 1 });
  const [savingUnidad, setSavingUnidad] = useState(false);

  // ── Ingredient stock error notification (from backend when stock exceeds ingredient availability) ──
  const [ingredientStockError, setIngredientStockError] = useState<{
    mensaje: string;
    ingredientes: Array<{ ingrediente: string; disponible: number; requerido: number; max_posible: number }>;
  } | null>(null);

  // ── Form-level validation error banner (replaces toast for field-specific errors) ──
  const [formError, setFormError] = useState<string | null>(null);

  // Track previous unidad_medida_id for price/stock conversion on unit change
  const prevUnidadMedidaIdRef = useRef<number | null>(null);

  // Tipo filter for unit dropdown — null means show all, a tipo value means show only same-tipo
  const [unidadTipoFilter, setUnidadTipoFilter] = useState<UnidadMedidaTipo | null>(null);

  // Cloudinary Upload Widget state (managed by shared hook)
  const [imagenPublicIds, setImagenPublicIds] = useState<string[]>([]);

  // ── Real-time admin WebSocket: listen for producto_actualizado events ──
  const isAdminOrStock = (() => {
    try {
      const roles = getUserRoles();
      return (roles.includes("ADMIN") || roles.includes("STOCK")) && !!getAccessToken();
    } catch {
      return false;
    }
  })();
  useAdminProductoWebSocket({ enabled: isAdminOrStock });

  // ── TanStack Query: products (paginated) ──
  const { data, isLoading, isError, error } = useProductos(skip, limit, debouncedSearch || undefined, undefined, sortBy || undefined, sortOrder || undefined);
  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  const editingProductName = useMemo(() => {
    if (!editingId) return null;
    return items.find(p => p.id === editingId)?.nombre ?? null;
  }, [editingId, items]);

  // ── UnidadMedida state and conversion factors ──
  // Always fetch ALL unidades so the ingredient table dropdown has the full list.
  // The product unit dropdown uses a locally-filtered subset (unidadesFiltradas).
  const [unidades, setUnidades] = useState<UnidadMedida[]>([]);

  useEffect(() => {
    let cancelled = false;
    // Retry with backoff: a transient auth/network failure must not silently
    // leave `factores` empty, which would disable the auto-calc of precio_base.
    const loadUnidades = (attempt: number) => {
      unidadesMedidaApi.getAll()
        .then((data) => {
          if (!cancelled) setUnidades(data);
        })
        .catch(() => {
          if (cancelled) return;
          if (attempt < 2) {
            setTimeout(() => loadUnidades(attempt + 1), 1500 * (attempt + 1));
          } else {
            addToast("error", "No se pudieron cargar las unidades de medida. Recargá la página.");
          }
        });
    };
    loadUnidades(0);
    return () => { cancelled = true; };
  }, []); // fetch once, never filter the API call

  // Locally-filtered subset for the product's unit dropdown (same-tipo lock when editing)
  const unidadesFiltradas = useMemo(() => {
    if (!unidadTipoFilter) return unidades;
    return unidades.filter(u => u.tipo === unidadTipoFilter);
  }, [unidades, unidadTipoFilter]);

  const factores = useMemo(() => {
    const map: Record<number, number> = {};
    for (const u of unidades) {
      map[u.id] = Number(u.factor_conversion);
    }
    return map;
  }, [unidades]);

  // ── Categories and ingredients for selectors (fetch all, not paginated) ──
  const [categoriaTree, setCategoriaTree] = useState<CategoriaTree[]>([]);
  const [allIngs, setAllIngs] = useState<Ingrediente[]>([]);

  useEffect(() => {
    categoriasApi.getTree().then(setCategoriaTree).catch(() => {});
    ingredientesApi.getAll(0, 1000).then(setAllIngs).catch(() => {});
  }, []);

  // ── Shared ingredients per product (warning: derived stock can be reduced) ──
  const [compartidosMap, setCompartidosMap] = useState<Record<number, string[]>>({});

  useEffect(() => {
    productosApi.getIngredientesCompartidos()
      .then((data) => {
        const map: Record<number, string[]> = {};
        for (const item of data) {
          map[item.producto_id] = item.ingredientes ?? [];
        }
        setCompartidosMap(map);
      })
      .catch(() => {});
  }, []);

  // ── TanStack Query mutations ──
  const createMutation = useCreateProducto();
  const updateMutation = useUpdateProducto();
  const deleteMutation = useDeleteProducto();

  const extractPublicId = (url: string): string => {
    try {
      const parts = url.split("/");
      const last = parts[parts.length - 1];
      const dotIdx = last.lastIndexOf(".");
      return dotIdx >= 0 ? last.substring(0, dotIdx) : last;
    } catch {
      return url;
    }
  };

  const handleAddToCart = (prod: Producto) => {
    // Pre-check: prevent adding if cart already at stock limit
    const currentCartItem = useCartStore.getState().items.find((i) => i.productoId === prod.id);
    const currentCartQty = currentCartItem?.cantidad ?? 0;
    if (currentCartQty + 1 > prod.stock_cantidad) {
      addToast("error", STOCK_EXCEEDED_MESSAGE);
      return;
    }

    const result = useCartStore.getState().addToCart(
      prod.id, prod.nombre, Number(prod.precio_actual), 1, prod.stock_cantidad,
    );
    if (!result.success) {
      addToast("error", STOCK_EXCEEDED_MESSAGE);
      return;
    }

    addToast("exito", `${prod.nombre} agregado al carrito`);
    triggerFeedback(prod.id);
  };

  const triggerFeedback = (productoId: number) => {
    setRecentlyAdded((prev) => new Set(prev).add(productoId));
    const existingTimer = addTimerRef.current.get(productoId);
    if (existingTimer) clearTimeout(existingTimer);
    const timer = setTimeout(() => {
      setRecentlyAdded((prev) => {
        const next = new Set(prev);
        next.delete(productoId);
        return next;
      });
      addTimerRef.current.delete(productoId);
    }, 1200);
    addTimerRef.current.set(productoId, timer);
  };

  // Cloudinary Upload Widget (shared hook, multiple mode)
  const { abrirWidget, eliminarImagen, uploadingImages } = useCloudinaryUpload("multiple");

  const handleDeleteImagen = async (publicId: string) => {
    await eliminarImagen(publicId);
    const idx = imagenPublicIds.indexOf(publicId);
    if (idx >= 0) {
      const currentUrls = form.getFieldValue("imagenes_url") ?? [];
      const newUrls = [...currentUrls];
      newUrls.splice(idx, 1);
      form.setFieldValue("imagenes_url", newUrls);
      setImagenPublicIds((prev) => prev.filter((id) => id !== publicId));
    }
  };

  // Load selected categories and ingredients when editing an existing product
  useEffect(() => {
    if (editingId) {
      Promise.all([
        productosApi.getCategorias(editingId),
        productosApi.getIngredientes(editingId),
      ]).then(([cats, ings]) => {
        setSelectedCategorias(cats.map(c => ({ id: c.categoria_id, nombre: c.categoria_nombre, descripcion: null })));
        const selectedIngs = ings.map(i => {
          const ing = allIngs.find(ai => ai.id === i.ingrediente_id);
          return { id: i.ingrediente_id, nombre: i.ingrediente_nombre, es_alergeno: ing ? ing.es_alergeno : false, cantidad: i.cantidad ?? 1, unidad_medida_id: i.unidad_medida_id ?? null, es_removible: i.es_removible };
        });
        setSelectedIngredientes(selectedIngs);
      });
    }
  }, [editingId, allIngs]);

  // Sync calculated price from selected ingredients (create mode only)
  const precioCalculadoRef = useRef(0);
  useEffect(() => {
    if (!editingId && selectedIngredientes.length > 0 && Object.keys(factores).length > 0) {
      const totalPrice = selectedIngredientes.reduce((sum, ing) => {
        const fullIng = allIngs.find(a => a.id === ing.id);
        const origen = ing.unidad_medida_id ?? fullIng?.unidad_medida_id ?? null;
        const destino = fullIng?.unidad_medida_id ?? null;
        const cantConv = convertirCantidad(ing.cantidad ?? 1, origen, destino, factores);
        return sum + Number(fullIng?.precio_actual ?? 0) * cantConv;
      }, 0);
      precioCalculadoRef.current = totalPrice;
      form.setFieldValue('precio_base', totalPrice);
    }
  }, [selectedIngredientes, editingId, allIngs, factores]);

  const form = useAppForm<ProductoFormValues>({
    defaultValues: {
      nombre: "",
      descripcion: "",
      precio_base: 0,
      precio_actual: 0,
      receta: "",
      tiempo_prep_min: 0,
      disponible: true,
      es_producto_terminado: false,
      imagenes_url: [],
      categorias_ids: [],
      ingredientes: [],
      unidad_medida_id: 5,
    },
    onSubmit: async ({ value }: { value: ProductoFormValues }) => {
      try {
        if (editingId) {
          if (stockEditOnly) {
            const updateData: Record<string, unknown> = {
              disponible: value.disponible,
              unidad_medida_id: value.unidad_medida_id,
            };
            // Only include stock_cantidad for es_producto_terminado products
            if (value.es_producto_terminado && value.stock_cantidad !== undefined) {
              updateData.stock_cantidad = value.stock_cantidad;
            }
            // Include ingredient changes for non-terminado products
            if (!value.es_producto_terminado && selectedIngredientes.length > 0) {
              updateData.ingredientes = selectedIngredientes.map(i => ({
                ingrediente_id: i.id,
                cantidad: i.cantidad ?? 1,
                unidad_medida_id: i.unidad_medida_id ?? null,
                es_removible: i.es_removible,
              }));
            }
            // Include image changes
            if (value.imagenes_url) {
              updateData.imagenes_url = value.imagenes_url;
            }
            await updateMutation.mutateAsync({ id: editingId, data: updateData });
          } else {
            const original = items.find(p => p.id === editingId);
            const changed: Record<string, unknown> = {};
            if (value.nombre !== original?.nombre) changed.nombre = value.nombre;
            if (value.descripcion !== (original?.descripcion ?? null)) changed.descripcion = value.descripcion;
            if (value.receta !== (original?.receta ?? null)) changed.receta = value.receta;
            if (Number(value.precio_base) !== Number(original?.precio_base ?? 0)) changed.precio_base = value.precio_base;
            if (Number(value.precio_actual) !== Number(original?.precio_actual ?? 0)) changed.precio_actual = value.precio_actual;
            if (value.disponible !== original?.disponible) changed.disponible = value.disponible;
            if (value.es_producto_terminado !== original?.es_producto_terminado) changed.es_producto_terminado = value.es_producto_terminado;
            if (JSON.stringify(value.imagenes_url) !== JSON.stringify(original?.imagenes_url ?? [])) {
              changed.imagenes_url = value.imagenes_url;
            }
            if (Number(value.tiempo_prep_min) !== Number(original?.tiempo_prep_min ?? 0)) changed.tiempo_prep_min = value.tiempo_prep_min;
            if (value.unidad_medida_id !== original?.unidad_medida_id) changed.unidad_medida_id = value.unidad_medida_id ?? null;
            changed.categorias = selectedCategorias.map(c => ({ categoria_id: c.id }));
            changed.ingredientes = selectedIngredientes.map(i => ({
              ingrediente_id: i.id,
              cantidad: i.cantidad ?? 1,
              unidad_medida_id: i.unidad_medida_id ?? null,
              es_removible: i.es_removible,
            }));
            await updateMutation.mutateAsync({ id: editingId, data: changed });
          }
          addToast('exito', 'Producto actualizado correctamente');
        } else {
          if (!value.es_producto_terminado && selectedIngredientes.length === 0 && Number(value.precio_base ?? 0) <= 0) {
            throw new Error("El precio base debe ser mayor a 0 cuando no hay ingredientes");
          }
          // Exclude stock_cantidad from API payload — backend derives stock from ingredients
          const { stock_cantidad: _sc, ...createData } = value;
          await createMutation.mutateAsync({
            ...createData,
            precio_actual: value.precio_actual,
            es_producto_terminado: value.es_producto_terminado,
            categorias_ids: selectedCategorias.map(c => c.id),
            ingredientes: selectedIngredientes.map(i => ({
              ingrediente_id: i.id,
              cantidad: i.cantidad ?? 1,
              unidad_medida_id: i.unidad_medida_id ?? null,
              es_removible: i.es_removible,
              es_principal: false,
              orden: 0,
            })),
            unidad_medida_id: value.unidad_medida_id || null,
          });
          addToast('exito', 'Producto creado correctamente');
        }
        handleCloseForm();
      } catch (err) {
        const parsed = parseApiError(err);

        // ── Ingredient-level stock error (entity-specific — must remain in page) ──
        if (isAxiosError(err) && err.response?.data) {
          const body = err.response.data as Record<string, unknown>;
          if (body.error === 'stock_insuficiente' && Array.isArray(body.ingredientes)) {
            const ings = body.ingredientes as Array<Record<string, unknown>>;
            if (ings.length > 0 && typeof ings[0].ingrediente === 'string') {
              setIngredientStockError({
                mensaje: parsed.detail || 'Stock insuficiente en los siguientes ingredientes',
                ingredientes: ings as Array<{ ingrediente: string; disponible: number; requerido: number; max_posible: number }>,
              });
              return;
            }
          }
        }

        // ── Business validation errors (entity-specific detail checks) ──
        if (parsed.detail) {
          if (parsed.detail.includes('precio actual no puede ser menor al precio base')) {
            setFormError('Precio de Venta no puede ser menor al Precio Base.');
            return;
          }
          if (parsed.detail.includes('precio base debe ser mayor a 0')) {
            setFormError('Precio Base debe ser mayor a 0 cuando el producto no tiene ingredientes ni es de reventa.');
            return;
          }
        }

        // ── Pydantic validation errors (422) — field-level messages ──
        if (parsed.validationErrors.length > 0) {
          setFormError(parsed.validationErrors.join('; '));
          return;
        }

        // ── Fallback: show detail string as toast ──
        const msg = parsed.detail || 'Error del servidor. Verifique los datos ingresados.';
        addToast('error', msg);
      }
    },
  });

  // ── Price/stock conversion when unidad_medida_id changes ──
  const watchedUnidadMedidaId = useStore(
    form.store,
    (state) => state.values.unidad_medida_id ?? null
  );

  useEffect(() => {
    const currentId = watchedUnidadMedidaId;

    // Tipo-locking: when editing, filter dropdown to same-tipo units after selection.
    // During creation, keep all tipos visible so the user can freely choose.
    if (currentId !== null && unidades.length > 0) {
      const selectedUnit = unidades.find(u => u.id === currentId);
      if (selectedUnit?.tipo && editingId) {
        setUnidadTipoFilter(selectedUnit.tipo);
      }
    }

    // First render: just track the current ID, no conversion
    if (prevUnidadMedidaIdRef.current === null) {
      prevUnidadMedidaIdRef.current = currentId;
      return;
    }

    // Guard: same unit (no-op) or null previous/current
    if (currentId === prevUnidadMedidaIdRef.current) return;
    if (currentId === null || prevUnidadMedidaIdRef.current === null) return;

    // Look up both units in the loaded unidades array
    const oldUnit = unidades.find(
      (u) => u.id === prevUnidadMedidaIdRef.current
    );
    const newUnit = unidades.find((u) => u.id === currentId);

    // Guard: both units must exist and have positive conversion factors
    if (!oldUnit?.factor_conversion || !newUnit?.factor_conversion) return;
    if (oldUnit.factor_conversion <= 0 || newUnit.factor_conversion <= 0) return;

    const oldFactor = Number(oldUnit.factor_conversion);
    const newFactor = Number(newUnit.factor_conversion);

    // Price conversion: newPrice = oldPrice * newFactor / oldFactor
    // (price is PER unit — smaller unit = smaller price)
    const convertPrice = (oldPrice: number) =>
      Math.round((oldPrice * newFactor / oldFactor) * 100) / 100;

    const oldPrecioBase = form.getFieldValue("precio_base") ?? 0;
    const oldPrecioActual = form.getFieldValue("precio_actual") ?? 0;

    form.setFieldValue("precio_base", convertPrice(Number(oldPrecioBase)));
    form.setFieldValue("precio_actual", convertPrice(Number(oldPrecioActual)));

    // Stock conversion: newStock = oldStock * oldFactor / newFactor
    // (stock is total quantity — smaller unit = larger number of units)
    const oldStock = form.getFieldValue("stock_cantidad") ?? 0;
    form.setFieldValue(
      "stock_cantidad",
      Math.round(Number(oldStock) * oldFactor / newFactor)
    );

    // Track new unit as "old" for next change
    prevUnidadMedidaIdRef.current = currentId;
  }, [watchedUnidadMedidaId, unidades]);

  // ── Precio de venta >= Precio Base ──
  const watchedPrecioBase = useStore(
    form.store,
    (state) => state.values.precio_base ?? 0
  );

  useEffect(() => {
    const base = Number(watchedPrecioBase);
    const actual = Number(form.getFieldValue('precio_actual') ?? 0);
    // When precio_base changes and precio_actual is below it, auto-bump
    if (base > 0 && actual < base) {
      form.setFieldValue('precio_actual', base);
    }
    // On first open/create, precio_actual defaults to precio_base
    if (base > 0 && actual === 0 && !editingId) {
      form.setFieldValue('precio_actual', base);
    }
  }, [watchedPrecioBase]);

  const handleStartCreate = () => {
    prevUnidadMedidaIdRef.current = null;
    setUnidadTipoFilter(null); // Show all units on create
    form.reset();
    setImagenPublicIds([]);
    setEditingId(null);
    setShowForm(true);
    setStockEditOnly(false);
    setFormError(null);
    setSelectedCategorias([]);
    setSelectedIngredientes([]);
  };

  const handleStartEdit = (prod: Producto) => {
    prevUnidadMedidaIdRef.current = null;
    form.reset({
      nombre: prod.nombre,
      descripcion: prod.descripcion ?? "",
      receta: prod.receta ?? "",
      precio_base: prod.precio_base,
      precio_actual: prod.precio_actual,
      stock_cantidad: prod.stock_cantidad,
      tiempo_prep_min: prod.tiempo_prep_min,
      disponible: prod.disponible,
      es_producto_terminado: prod.es_producto_terminado,
      imagenes_url: prod.imagenes_url,
      unidad_medida_id: prod.unidad_medida_id ?? null,
    }, { keepDefaultValues: true });
    setImagenPublicIds(prod.imagenes_url.map(extractPublicId));
    setEditingId(prod.id);
    setShowForm(true);
    setStockEditOnly(false);
    setSelectedCategorias([]);
    setSelectedIngredientes([]);

    // Detect tipo from product's current unit to pre-filter dropdown
    if (prod.unidad_medida_id) {
      const fromState = unidades.find(u => u.id === prod.unidad_medida_id);
      if (fromState?.tipo) {
        setUnidadTipoFilter(fromState.tipo);
      } else {
        // unidades might be stale/empty — fetch all to find tipo
        unidadesMedidaApi.getAll().then(all => {
          const u = all.find(x => x.id === prod.unidad_medida_id);
          setUnidadTipoFilter(u?.tipo ?? null);
        }).catch(() => {});
      }
    }
  };

  const handleStartStockEdit = (prod: Producto) => {
    prevUnidadMedidaIdRef.current = null;
    form.reset({
      nombre: prod.nombre,
      descripcion: prod.descripcion ?? "",
      receta: prod.receta ?? "",
      precio_base: prod.precio_base,
      precio_actual: prod.precio_actual,
      stock_cantidad: prod.stock_cantidad,
      tiempo_prep_min: prod.tiempo_prep_min,
      disponible: prod.disponible,
      es_producto_terminado: prod.es_producto_terminado,
      imagenes_url: prod.imagenes_url,
      unidad_medida_id: prod.unidad_medida_id ?? null,
    }, { keepDefaultValues: true });
    setImagenPublicIds(prod.imagenes_url.map(extractPublicId));
    setEditingId(prod.id);
    setShowForm(true);
    setStockEditOnly(true);
    setSelectedCategorias([]);
    setSelectedIngredientes([]);

    // Detect tipo from product's current unit to pre-filter dropdown
    if (prod.unidad_medida_id) {
      const fromState = unidades.find(u => u.id === prod.unidad_medida_id);
      if (fromState?.tipo) {
        setUnidadTipoFilter(fromState.tipo);
      } else {
        unidadesMedidaApi.getAll().then(all => {
          const u = all.find(x => x.id === prod.unidad_medida_id);
          setUnidadTipoFilter(u?.tipo ?? null);
        }).catch(() => {});
      }
    }
  };

  const handleCloseForm = () => {
    prevUnidadMedidaIdRef.current = null;
    setUnidadTipoFilter(null); // Reset filter so all units load again
    form.reset();
    setImagenPublicIds([]);
    setShowForm(false);
    setEditingId(null);
    setStockEditOnly(false);
    setSelectedCategorias([]);
    setSelectedIngredientes([]);
    setShowCategoriaSelector(false);
    setShowIngredienteSelector(false);
    setIngredientStockError(null);
    setFormError(null);
  };

  const handleOpenStockDetail = async (p: Producto) => {
    setShowStockDetail(p);
    setStockDetailData([]);
    setStockDetailLoading(true);
    try {
      const data = await productosApi.getIngredientesStockDetail(p.id);
      setStockDetailData(data);
    } catch {
      setStockDetailData([]);
    } finally {
      setStockDetailLoading(false);
    }
  };

  const handleCreateUnidad = async () => {
    if (!newUnidad.nombre.trim() || !newUnidad.simbolo.trim()) return;
    setSavingUnidad(true);
    try {
      const created = await unidadesMedidaApi.create({
        nombre: newUnidad.nombre.trim(),
        simbolo: newUnidad.simbolo.trim(),
        tipo: newUnidad.tipo,
        factor_conversion: newUnidad.factor_conversion,
      });
      // Refresh unidades list
      const refreshed = await unidadesMedidaApi.getAll();
      setUnidades(refreshed);
      // Auto-select the newly created unit
      form.setFieldValue('unidad_medida_id', created.id);
      setShowNewUnidadForm(false);
      setNewUnidad({ nombre: '', simbolo: '', tipo: 'unidad', factor_conversion: 1 });
      addToast('exito', `Unidad "${created.simbolo}" creada`);
    } catch (err) {
      addToast('error', 'Error al crear la unidad');
    } finally {
      setSavingUnidad(false);
    }
  };

  const handleDelete = (id: number) => {
    const product = items.find(p => p.id === id);
    crud.openDeleteConfirm(id, product?.nombre ?? `#${id}`);
  };

  const handleConfirmDelete = async () => {
    if (!crud.deleteTarget) return;
    try {
      await deleteMutation.mutateAsync(crud.deleteTarget.id);
      addToast('exito', 'Producto eliminado');
    } catch (err) {
      addToast('error', (err as Error).message);
    } finally {
      crud.closeDeleteConfirm();
    }
  };

  // Build columns based on role
  const columns: DataTableColumn<Producto>[] = [
    ...(!readOnly ? [{ key: "id" as const, label: "Codigo", sortable: true, hideOnMobile: true, render: (p: Producto) => <span className="text-gray-500 text-xs">{p.id}</span> }] : []),
    { key: "nombre" as const, label: "Nombre", render: (p: Producto) => <span className="font-medium text-gray-800">{p.nombre}</span> },
    {
      key: "precio_actual" as const,
      label: "Precio",
      sortable: true,
      render: (p: Producto) => (
        <span className="font-mono text-sm">
          {formatCurrency(p.precio_actual)}
          {p.tiene_ingredientes && !p.es_producto_terminado && role !== 'client' && (
            <span className="text-xs text-blue-600 font-medium ml-1">(calc)</span>
          )}
        </span>
      ),
    },
    ...(!readOnly ? [{
      key: "stock_cantidad" as const,
      label: "Stock",
      headerTitle: "Stock derivado de los ingredientes del producto. Puede verse reducido si otros productos comparten el mismo ingrediente.",
      sortable: true,
      render: (p: Producto) => {
        const compartidos = compartidosMap[p.id] ?? [];
        return (
          <span className="inline-flex items-center gap-1.5">
            {p.stock_cantidad === 0 ? (
              <button
                type="button"
                onClick={() => handleOpenStockDetail(p)}
                className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-700 hover:bg-red-200 transition-colors cursor-pointer"
                title="Ver que ingredientes limitan el stock"
              >
                Sin stock
              </button>
            ) : (
              <span className="font-mono font-semibold text-sm text-green-700">
                {p.stock_cantidad}
              </span>
            )}
            {compartidos.length > 0 && (
              <span
                title={`Comparte ingrediente(s) con otros productos: ${compartidos.join(", ")}`}
                aria-label={`Comparte ingredientes: ${compartidos.join(", ")}`}
                className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-amber-100 text-amber-700 text-[10px] font-bold cursor-help"
              >
                !
              </span>
            )}
          </span>
        );
      },
    }] : []),
    ...(!readOnly && !isStockMode ? [{
      key: "tiempo_prep_min" as const,
      label: "Prep. (min)",
      sortable: true,
      hideOnMobile: true,
      render: (p: Producto) => <span className="text-sm">{p.tiempo_prep_min}</span>,
    }] : []),
    {
      key: "disponible" as const,
      label: "Disponible",
      sortable: true,
      render: (p: Producto) => {
        const isUnavailable = !p.disponible || p.stock_cantidad <= 0;
        return (
          <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${isUnavailable ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
            {isUnavailable ? "No disponible" : "Disponible"}
          </span>
        );
      },
    },
    ...(!readOnly ? [{
      key: "es_producto_terminado" as const,
      label: "Producto Terminado",
      sortable: true,
      hideOnMobile: true,
      render: (p: Producto) => (
        <span className={p.es_producto_terminado ? "text-green-600 font-bold" : "text-gray-600"}>
          {p.es_producto_terminado ? "Sí" : "No"}
        </span>
      ),
    }] : []),

    ...(!readOnly ? [{
      key: "acciones" as const,
      label: "Acciones",
      render: (p: Producto) => (
        <div className="flex gap-1 flex-wrap">
          {!isStockMode && (
            <EditButton onClick={() => handleStartEdit(p)} />
          )}
          {isStockMode && (
            <button onClick={() => handleStartStockEdit(p)}
              className="bg-amber-700 text-white px-2 py-1 rounded text-xs cursor-pointer hover:bg-amber-800 transition-colors">Stock</button>
          )}
          {!isStockMode && !hideDelete && (
            <DeleteButton onClick={() => handleDelete(p.id)} />
          )}
        </div>
      ),
    }] : []),
    ...(role === 'client' ? [{
      key: "carrito" as const,
      label: "Carrito",
      render: (p: Producto) => {
        let addable = true;
        let disabledReason = '';
        if (!p.disponible) { addable = false; disabledReason = 'No disponible'; }
        else if (p.stock_cantidad <= 0) { addable = false; disabledReason = 'Sin stock'; }

        if (!addable) {
          return (
            <button disabled className="px-2 py-1 rounded text-sm bg-gray-400 text-gray-700 cursor-not-allowed" title={disabledReason}>
              {disabledReason}
            </button>
          );
        }

        return (
          <button onClick={() => handleAddToCart(p)}
            className={`px-2 py-1 rounded text-sm cursor-pointer transition-colors ${
              recentlyAdded.has(p.id) ? "bg-green-600 text-white" : "bg-blue-600 text-white hover:bg-blue-700"
            }`}>
            {recentlyAdded.has(p.id) ? "OK Agregado" : "Agregar al carrito"}
          </button>
        );
      },
    }] : []),
  ];

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">{role === 'client' ? 'Menu' : 'Gestion de Productos'}</h1>
      <ErrorBanner isError={isError} error={error} message="Error al cargar" />

      {/* Toolbar */}
      <CrudToolbar
        searchValue={search}
        onSearchChange={(value) => { setSearch(value); crud.handlePageChange(0); }}
        searchPlaceholder="Filtrar por nombre..."
        onCreateClick={!hideCreate ? handleStartCreate : undefined}
        createLabel="Crear Producto"
        onExportClick={!hideExport ? () => exportToExcel(items.filter(p => p.nombre.toLowerCase().includes(search.toLowerCase())).map(({ id, nombre, precio_actual, stock_cantidad, disponible, tiempo_prep_min }) => ({
            id, nombre, Precio: precio_actual, Stock: stock_cantidad, "Tiempo prep. (min)": tiempo_prep_min, Disponible: disponible ? "Si" : "No",
          })), "productos") : undefined}
        exportLabel="Exportar Excel"
      />

      {/* Create/edit form */}
      {showForm && (!hideCreate || stockEditOnly) && (
        <form onSubmit={(e) => { e.preventDefault(); e.stopPropagation(); void form.handleSubmit(); }} className="border p-4 mb-4 rounded bg-gray-50">
          {/* ── Ingredient stock error panel ── */}
          {ingredientStockError && (
            <div className="mb-4 p-3 border border-amber-400 bg-amber-50 rounded">
              <p className="text-amber-800 font-semibold text-sm mb-2">
                {ingredientStockError.mensaje}
              </p>
              <table className="w-full text-xs border-collapse border border-amber-200 mb-2">
                <thead>
                  <tr className="bg-amber-100">
                    <th className="border border-amber-200 p-1 text-left">Ingrediente</th>
                    <th className="border border-amber-200 p-1 text-right">Disponible</th>
                    <th className="border border-amber-200 p-1 text-right">Requerido</th>
                    <th className="border border-amber-200 p-1 text-right">Max. productos</th>
                  </tr>
                </thead>
                <tbody>
                  {ingredientStockError.ingredientes.map((ing, i) => (
                    <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-amber-50'}>
                      <td className="border border-amber-200 p-1 font-medium">{ing.ingrediente}</td>
                      <td className="border border-amber-200 p-1 text-right">{ing.disponible}</td>
                      <td className="border border-amber-200 p-1 text-right text-red-600 font-medium">{ing.requerido}</td>
                      <td className="border border-amber-200 p-1 text-right">{ing.max_posible}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="flex gap-2">
                <button type="button" onClick={() => setIngredientStockError(null)}
                  className="text-xs bg-gray-400 text-white px-3 py-1 rounded cursor-pointer hover:bg-gray-500">
                  Cerrar
                </button>
                <button type="button" onClick={() => { setIngredientStockError(null); navigate('/ingredientes'); }}
                  className="text-xs bg-blue-600 text-white px-3 py-1 rounded cursor-pointer hover:bg-blue-700">
                  Ir a Ingredientes para subir stock
                </button>
              </div>
            </div>
          )}
          {stockEditOnly ? (
            <>
              {editingProductName && (
                <h2 className="text-lg font-bold text-amber-800 mb-3">
                  Editando stock de: {editingProductName}
                </h2>
              )}
              <div className="grid grid-cols-2 gap-4 mb-4">
              {/* Stock field: only editable for es_producto_terminado products.
                  Regular products derive stock from ingredient availability. */}
              {form.getFieldValue('es_producto_terminado') && (
              <form.Field name="stock_cantidad">
                {(field) => (
                  <div>
                    <label className="block text-sm font-medium">Stock (manual)</label>
                    <DecimalInput
                      value={field.state.value ?? 0}
                      onChange={(v) => field.handleChange(v)}
                      onBlur={field.handleBlur}
                      decimals={0}
                      min={0}
                      step={1}
                    />
                    {field.state.meta.errors && (
                      <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
                    )}
                  </div>
                )}
              </form.Field>
              )}
              <form.Field name="disponible">
                {(field) => (
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium">Disponible</label>
                    <input type="checkbox" checked={field.state.value ?? true}
                      onChange={(e) => field.handleChange(e.target.checked)} />
                  </div>
                )}
              </form.Field>
              {!readOnly && (
                <form.Field name="unidad_medida_id">
                  {(field) => (
                    <div>
                      <label className="block text-sm font-medium">Unidad de Medida</label>
                      <select value={field.state.value ?? ""}
                        onChange={(e) => field.handleChange(e.target.value ? Number(e.target.value) : null)}
                        onBlur={field.handleBlur}
                        className="border px-2 py-1 rounded w-full">
                        <option value="5">Porcion</option>
                        {unidadesFiltradas.filter(u => u.id !== 5).map((u) => (
                          <option key={u.id} value={u.id}>{u.simbolo} ({u.nombre})</option>
                        ))}
                    </select>
                    {!showNewUnidadForm ? (
                      <button type="button" onClick={() => setShowNewUnidadForm(true)}
                        className="text-xs text-blue-600 hover:text-blue-800 mt-1 cursor-pointer">
                        + Nueva unidad de medida
                      </button>
                    ) : (
                      <div className="mt-2 p-2 border rounded bg-white space-y-1">
                        <div className="flex gap-2">
                          <div className="flex-1">
                            <input type="text" placeholder="Nombre (ej: Docena)"
                              value={newUnidad.nombre}
                              onChange={(e) => setNewUnidad(prev => ({ ...prev, nombre: e.target.value }))}
                              maxLength={50}
                              className="border px-2 py-1 rounded text-sm w-full" />
                            <span className={`text-xs ${newUnidad.nombre.length >= 50 ? 'text-red-600' : 'text-gray-400'}`}>
                              {newUnidad.nombre.length} / 50 caracteres
                            </span>
                          </div>
                          <div>
                            <input type="text" placeholder="Simbolo (ej: doc)"
                              value={newUnidad.simbolo}
                              onChange={(e) => setNewUnidad(prev => ({ ...prev, simbolo: e.target.value }))}
                              maxLength={10}
                              className="border px-2 py-1 rounded text-sm w-20" />
                            <span className={`text-xs ${newUnidad.simbolo.length >= 10 ? 'text-red-600' : 'text-gray-400'}`}>
                              {newUnidad.simbolo.length} / 10 caracteres
                            </span>
                          </div>
                        </div>
                        <div className="flex gap-2 items-center">
                          <select value={newUnidad.tipo}
                            onChange={(e) => setNewUnidad(prev => ({ ...prev, tipo: e.target.value as UnidadMedidaTipo }))}
                            className="border px-2 py-1 rounded text-sm">
                            <option value="unidad">Unidad</option>
                            <option value="masa">Masa</option>
                            <option value="volumen">Volumen</option>
                            <option value="area">Area</option>
                          </select>
                          <label className="text-xs text-gray-500">Factor Conversión:</label>
                          <DecimalInput value={newUnidad.factor_conversion}
                            onChange={(v) => setNewUnidad(prev => ({ ...prev, factor_conversion: v }))}
                            decimals={3} min={0.001} step={0.001} width="w-20" />
                        </div>
                        {newUnidad.factor_conversion > 0 && (() => {
                          const base = unidades.find(u => u.tipo === newUnidad.tipo && u.factor_conversion === 1);
                          const nombre = newUnidad.nombre.trim() || '?';
                          const baseSimbolo = base ? base.simbolo : '?';
                          return (
                            <p className="text-xs text-blue-700 bg-blue-50 p-1 rounded">
                              1 {nombre} = {newUnidad.factor_conversion} {baseSimbolo}
                            </p>
                          );
                        })()}
                        <div className="flex gap-2">
                          <button type="button" onClick={handleCreateUnidad}
                            disabled={savingUnidad || !newUnidad.nombre.trim() || !newUnidad.simbolo.trim()}
                            className="bg-green-600 text-white px-3 py-1 rounded text-xs cursor-pointer disabled:opacity-50">
                            {savingUnidad ? 'Guardando...' : 'Crear'}
                          </button>
                          <button type="button" onClick={() => { setShowNewUnidadForm(false); setNewUnidad({ nombre: '', simbolo: '', tipo: 'unidad', factor_conversion: 1 }); }}
                            className="bg-gray-400 text-white px-3 py-1 rounded text-xs cursor-pointer">Cancelar</button>
                        </div>
                      </div>
                    )}
                    {field.state.value != null && (() => {
                      const selected = unidades.find(u => u.id === field.state.value);
                      if (!selected) return null;
                      const base = unidades.find(u => u.tipo === selected.tipo && u.factor_conversion === 1);
                      if (!base || base.id === selected.id) return null;
                      return (
                        <p className="text-xs text-gray-500 mt-1">
                          Unidad base: {base.nombre} ({base.simbolo})
                        </p>
                      );
                    })()}
                  </div>
                  )}
                </form.Field>
              )}
            </div>
            {/* Ingredient table: show for non-terminado products in stock edit mode */}
            {!form.getFieldValue('es_producto_terminado') && selectedIngredientes.length > 0 && (
              <div className="border p-4 mb-4 rounded bg-gray-50">
                <h3 className="text-lg font-medium mb-2">Ingredientes</h3>
                <table className="w-full border-collapse border mb-2">
                  <thead><tr className="bg-gray-200">
                    <th className="border p-2 text-left">Nombre</th>
                    <th className="border p-2 text-left">Stock Disponible</th>
                    <th className="border p-2 text-left">Alergeno</th>
                    <th className="border p-2 text-left">Cantidad</th>
                  </tr></thead>
                  <tbody>
                    {selectedIngredientes.map((i) => {
                      const ingFull = allIngs.find(ai => ai.id === i.id);
                      return (
                      <tr key={i.id}>
                        <td className="border p-2">
                          <button
                            type="button"
                            onClick={() => navigate(`/ingredientes?edit=${i.id}`)}
                            className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                            title={`Editar ingrediente "${i.nombre}"`}
                          >
                            {i.nombre}
                          </button>
                        </td>
                        <td className="border p-2 font-mono">{ingFull ? `${ingFull.stock_actual} ${ingFull.unidad_medida_simbolo ?? ""}` : "—"}</td>
                        <td className="border p-2">{i.es_alergeno ? "Si" : "No"}</td>
                        <td className="border p-2">
                          <div className="flex items-center gap-2">
                            <DecimalInput
                              value={i.cantidad}
                              onChange={(val) => {
                                setSelectedIngredientes(prev => prev.map(si =>
                                  si.id === i.id ? { ...si, cantidad: val } : si
                                ));
                              }}
                              min={0.01} step={0.01}
                              decimals={2}
                              className="w-24"
                            />
                            <select
                              value={i.unidad_medida_id ?? ''}
                              onChange={(e) => {
                                const newUnitId = e.target.value ? Number(e.target.value) : null;
                                setSelectedIngredientes(prev => prev.map(si => {
                                  if (si.id !== i.id) return si;
                                  const oldUnitId = si.unidad_medida_id;
                                  const newCant = oldUnitId && newUnitId
                                    ? convertirCantidad(si.cantidad, oldUnitId, newUnitId, factores)
                                    : si.cantidad;
                                  return { ...si, cantidad: newCant, unidad_medida_id: newUnitId };
                                }));
                              }}
                              className="border rounded p-1 text-sm"
                            >
                              <option value="">unidad/es</option>
                              {unidades.filter(u => {
                                const ingFullUnit = ingFull ? unidades.find(un => un.id === ingFull.unidad_medida_id) : undefined;
                                return !ingFullUnit || u.tipo === ingFullUnit.tipo;
                              }).map(u => (
                                <option key={u.id} value={u.id}>{u.simbolo}</option>
                              ))}
                            </select>
                          </div>
                        </td>
                      </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </>
          ) : (
            <>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <form.Field name="nombre" validators={{ onChange: required('El nombre es obligatorio') }}>
                {(field) => (
                  <div>
                    <label className="block text-sm font-medium">Nombre</label>
                    <input value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      onBlur={field.handleBlur}
                      className="border px-2 py-1 rounded w-full" />
                    {field.state.meta.errors && (
                      <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
                    )}
                  </div>
                )}
              </form.Field>
              <form.Field name="descripcion">
                {(field) => (
                  <div>
                    <label className="block text-sm font-medium">Descripcion</label>
                    <input value={field.state.value ?? ""}
                      onChange={(e) => field.handleChange(e.target.value)}
                      onBlur={field.handleBlur}
                      className="border px-2 py-1 rounded w-full" />
                    {field.state.meta.errors && (
                      <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
                    )}
                  </div>
                )}
              </form.Field>
              <div>
                <label className="block text-sm font-medium">
                  Precio Base
                  {(() => {
                    const unidadId = form.getFieldValue('unidad_medida_id');
                    if (unidadId) {
                      const u = unidades.find(un => un.id === unidadId);
                      if (u) return <span className="text-gray-500 font-normal"> (por {u.simbolo})</span>;
                    }
                    return null;
                  })()}
                </label>
                {(() => {
                  const editingProduct = editingId ? items.find(p => p.id === editingId) : null;
                  const hasIngredients = editingProduct?.tiene_ingredientes ?? false;
                  const isProductoTerminadoValue = form.getFieldValue('es_producto_terminado');
                  const precioDisabled = isProductoTerminadoValue ? false : (editingId ? hasIngredients : selectedIngredientes.length > 0);
                  return (
                    <form.Field name="precio_base"
                      validators={{
                        onChange: ({ value }) => {
                          // Only validate when field is user-editable: not es_producto_terminado and no ingredients
                          const isProductoTerminadoVal = form.getFieldValue('es_producto_terminado');
                          if (isProductoTerminadoVal || selectedIngredientes.length > 0) return undefined;
                          return value != null && Number(value) <= 0
                            ? 'El precio base debe ser mayor a 0'
                            : undefined;
                        }
                      }}
                    >
                      {(field) => (
                        <>
                          <DecimalInput
                            value={Number(field.state.value) || 0}
                            onChange={(v) => field.handleChange(v)}
                            onBlur={field.handleBlur}
                            decimals={2}
                            min={0}
                            step={0.01}
                            isCurrency
                            disabled={precioDisabled}
                            className={precioDisabled ? "cursor-not-allowed" : ""}
                          />
                          {(editingId && hasIngredients) || (!editingId && selectedIngredientes.length > 0) ? (
                            <p className="text-xs text-gray-500 mt-1 italic">
                              {!editingId
                                ? (selectedIngredientes.length === 1
                                    ? 'Calculado desde 1 ingrediente'
                                    : `Calculado desde ${selectedIngredientes.length} ingredientes`)
                                : 'Calculado desde ingredientes'}
                            </p>
                          ) : null}
                          {field.state.meta.errors && (
                            <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
                          )}
                        </>
                      )}
                    </form.Field>
                  );
                })()}
              </div>
              <div>
                <label className="block text-sm font-medium">
                  Precio de venta
                  {(() => {
                    const unidadId = form.getFieldValue('unidad_medida_id');
                    if (unidadId) {
                      const u = unidades.find(un => un.id === unidadId);
                      if (u) return <span className="text-gray-500 font-normal"> (por {u.simbolo})</span>;
                    }
                    return null;
                  })()}
                </label>
                <form.Field name="precio_actual"
                  validators={{
                    onChange: ({ value }) => {
                      const base = form.getFieldValue('precio_base');
                      if (base != null && value != null && Number(value) < Number(base)) {
                        return `No puede ser menor al precio base (${formatCurrency(base)})`;
                      }
                      return undefined;
                    }
                  }}>
                  {(field) => (
                    <>
                    <DecimalInput
                      value={field.state.value ?? 0}
                      onChange={(v) => field.handleChange(v)}
                      onBlur={field.handleBlur}
                      decimals={2}
                      min={0}
                      step={0.01}
                      isCurrency
                    />
                    {field.state.meta.errors && (
                      <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
                    )}
                    </>
                  )}
                </form.Field>
              </div>
              {!form.getFieldValue('es_producto_terminado') && (
                <div className="col-span-2">
                  <form.Field name="receta">
                    {(field) => (
                      <div>
                        <label className="block text-sm font-medium mb-1">Receta / Preparacion</label>
                      <textarea value={field.state.value ?? ""}
                        onChange={(e) => field.handleChange(e.target.value)}
                        onBlur={field.handleBlur}
                        rows={4}
                        placeholder="Ej: 200 g de harina, 2 huevos, 1 taza de leche. Mezclar y cocinar a fuego medio..."
                        className="w-full border border-gray-300 px-3 py-2 rounded text-sm" />
                    </div>
                  )}
                </form.Field>
              </div>
              )}
              {/* Stock field: only editable for es_producto_terminado products.
                  Regular products derive stock from ingredient availability. */}
              {form.getFieldValue('es_producto_terminado') && (
              <form.Field name="stock_cantidad">
                {(field) => {
                  return (
                  <div>
                    <label className="block text-sm font-medium">Stock (manual)</label>
                    <DecimalInput
                      value={field.state.value ?? 0}
                      onChange={(v) => field.handleChange(v)}
                      onBlur={field.handleBlur}
                      decimals={0}
                      min={0}
                      step={1}
                    />
                    {field.state.meta.errors && (
                      <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
                    )}
                  </div>
                  );
                }}
              </form.Field>
              )}
              <form.Field name="tiempo_prep_min">
                {(field) => (
                  <div>
                    <label className="block text-sm font-medium">Tiempo de preparacion (minutos)</label>
                    <DecimalInput
                      value={field.state.value ?? 0}
                      onChange={(v) => field.handleChange(v)}
                      onBlur={field.handleBlur}
                      decimals={0}
                      min={0}
                      step={1}
                    />
                    {field.state.meta.errors && (
                      <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
                    )}
                  </div>
                )}
              </form.Field>
              <form.Field name="disponible">
                {(field) => (
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium">Disponible</label>
                    <input type="checkbox" checked={field.state.value ?? true}
                      onChange={(e) => field.handleChange(e.target.checked)} />
                  </div>
                )}
              </form.Field>
              <form.Field name="es_producto_terminado">
                {(field) => (
                  <div className="flex items-center gap-2">
                    <input type="checkbox" checked={field.state.value ?? false}
                      onChange={(e) => {
                        const newValue = e.target.checked;
                        if (newValue && selectedIngredientes.length > 0) {
                          const confirmed = window.confirm(
                            "Este producto tiene ingredientes asignados. Al marcarlo como Producto Terminado se eliminaran todos los ingredientes. Desea continuar?"
                          );
                          if (confirmed) {
                            setSelectedIngredientes([]);
                            field.handleChange(newValue);
                          }
                        } else {
                          field.handleChange(newValue);
                        }
                      }}
                      className="cursor-pointer" />
                    <label className="text-sm font-medium">
                      Producto terminado (se compra y revende)
                    </label>
                  </div>
                )}
              </form.Field>
              <form.Field name="unidad_medida_id">
                {(field) => (
                  <div>
                    <label className="block text-sm font-medium">Unidad de Medida</label>
                    <select value={field.state.value ?? ""}
                      onChange={(e) => field.handleChange(e.target.value ? Number(e.target.value) : null)}
                      className="border px-2 py-1 rounded w-full">
                      <option value="5">Porcion</option>
                      {["masa", "volumen", "unidad", "area"].map((tipo) => {
                        const grupo = unidadesFiltradas.filter((u) => u.tipo === tipo && u.id !== 5);
                        if (grupo.length === 0) return null;
                        return (
                          <optgroup key={tipo} label={tipo.charAt(0).toUpperCase() + tipo.slice(1)}>
                            {grupo.map((u) => (
                              <option key={u.id} value={u.id}>{u.nombre} ({u.simbolo})</option>
                            ))}
                          </optgroup>
                        );
                      })}
                    </select>
                    {!showNewUnidadForm ? (
                      <button type="button" onClick={() => setShowNewUnidadForm(true)}
                        className="text-xs text-blue-600 hover:text-blue-800 mt-1 cursor-pointer">
                        + Nueva unidad de medida
                      </button>
                    ) : (
                      <div className="mt-2 p-2 border rounded bg-white space-y-1">
                        <div className="flex gap-2">
                          <div className="flex-1">
                            <input type="text" placeholder="Nombre (ej: Docena)"
                              value={newUnidad.nombre}
                              onChange={(e) => setNewUnidad(prev => ({ ...prev, nombre: e.target.value }))}
                              maxLength={50}
                              className="border px-2 py-1 rounded text-sm w-full" />
                            <span className={`text-xs ${newUnidad.nombre.length >= 50 ? 'text-red-600' : 'text-gray-400'}`}>
                              {newUnidad.nombre.length} / 50 caracteres
                            </span>
                          </div>
                          <div>
                            <input type="text" placeholder="Simbolo (ej: doc)"
                              value={newUnidad.simbolo}
                              onChange={(e) => setNewUnidad(prev => ({ ...prev, simbolo: e.target.value }))}
                              maxLength={10}
                              className="border px-2 py-1 rounded text-sm w-20" />
                            <span className={`text-xs ${newUnidad.simbolo.length >= 10 ? 'text-red-600' : 'text-gray-400'}`}>
                              {newUnidad.simbolo.length} / 10 caracteres
                            </span>
                          </div>
                        </div>
                        <div className="flex gap-2 items-center">
                          <select value={newUnidad.tipo}
                            onChange={(e) => setNewUnidad(prev => ({ ...prev, tipo: e.target.value as UnidadMedidaTipo }))}
                            className="border px-2 py-1 rounded text-sm">
                            <option value="unidad">Unidad</option>
                            <option value="masa">Masa</option>
                            <option value="volumen">Volumen</option>
                            <option value="area">Area</option>
                          </select>
                          <label className="text-xs text-gray-500">Factor Conversión:</label>
                          <DecimalInput value={newUnidad.factor_conversion}
                            onChange={(v) => setNewUnidad(prev => ({ ...prev, factor_conversion: v }))}
                            decimals={3} min={0.001} step={0.001} width="w-20" />
                        </div>
                        {newUnidad.factor_conversion > 0 && (() => {
                          const base = unidades.find(u => u.tipo === newUnidad.tipo && u.factor_conversion === 1);
                          const nombre = newUnidad.nombre.trim() || '?';
                          const baseSimbolo = base ? base.simbolo : '?';
                          return (
                            <p className="text-xs text-blue-700 bg-blue-50 p-1 rounded">
                              1 {nombre} = {newUnidad.factor_conversion} {baseSimbolo}
                            </p>
                          );
                        })()}
                        <div className="flex gap-2">
                          <button type="button" onClick={handleCreateUnidad}
                            disabled={savingUnidad || !newUnidad.nombre.trim() || !newUnidad.simbolo.trim()}
                            className="bg-green-600 text-white px-3 py-1 rounded text-xs cursor-pointer disabled:opacity-50">
                            {savingUnidad ? 'Guardando...' : 'Crear'}
                          </button>
                          <button type="button" onClick={() => { setShowNewUnidadForm(false); setNewUnidad({ nombre: '', simbolo: '', tipo: 'unidad', factor_conversion: 1 }); }}
                            className="bg-gray-400 text-white px-3 py-1 rounded text-xs cursor-pointer">Cancelar</button>
                        </div>
                      </div>
                    )}
                    {field.state.value != null && (() => {
                      const selected = unidades.find(u => u.id === field.state.value);
                      if (!selected) return null;
                      const base = unidades.find(u => u.tipo === selected.tipo && u.factor_conversion === 1);
                      if (!base || base.id === selected.id) return null;
                      return (
                        <p className="text-xs text-gray-500 mt-1">
                          Unidad base: {base.nombre} ({base.simbolo})
                        </p>
                      );
                    })()}
                  </div>
                )}
              </form.Field>
            </div>
            </>
          )}

          {/* Images section: available in both full edit and stock edit modes */}
          <div className="border p-4 mb-4 rounded bg-gray-50">
              <h3 className="text-lg font-medium mb-2">Imagenes</h3>
              <ImageCarousel
                images={form.getFieldValue("imagenes_url") ?? []}
                publicIds={imagenPublicIds}
                onDelete={handleDeleteImagen}
                readOnly={false}
                variant="thumbs"
                className="max-w-xs"
              />
              <button
                type="button"
                onClick={() => abrirWidget((secureUrl, publicId) => {
                  const currentUrls = form.getFieldValue("imagenes_url") ?? [];
                  form.setFieldValue("imagenes_url", [...currentUrls, secureUrl]);
                  setImagenPublicIds((prev) => [...prev, publicId]);
                })}
                disabled={uploadingImages}
                className="mt-3 bg-blue-600 text-white px-4 py-1 rounded cursor-pointer disabled:opacity-50 hover:bg-blue-700"
              >
                {uploadingImages ? "Subiendo..." : "Subir imagenes"}
              </button>
            </div>

          {!hideCreate && !isStockMode && (
            <>
              <div className="border p-4 mb-4 rounded bg-gray-50">
                <h3 className="text-lg font-medium mb-2">Categorias</h3>
                {selectedCategorias.length > 0 && (
                  <table className="w-full border-collapse border mb-2">
                    <thead><tr className="bg-gray-200">
                      <th className="border p-2 text-left">Nombre</th>
                      <th className="border p-2 text-left">Descripcion</th>
                      <th className="border p-2 text-left">Accion</th>
                    </tr></thead>
                    <tbody>
                      {selectedCategorias.map((c) => (
                        <tr key={c.id}>
                          <td className="border p-2">{c.nombre}</td>
                          <td className="border p-2">{c.descripcion ?? "-"}</td>
                          <td className="border p-2">
                            <button type="button" onClick={() => setSelectedCategorias(prev => prev.filter(sc => sc.id !== c.id))} className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer">Quitar</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                <button type="button" onClick={() => setShowCategoriaSelector(true)} className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">Seleccionar Categorias</button>
              </div>

              {!form.getFieldValue('es_producto_terminado') && (
              <div className="border p-4 mb-4 rounded bg-gray-50">
                <h3 className="text-lg font-medium mb-2">Ingredientes</h3>
                {selectedIngredientes.length > 0 && (
                  <table className="w-full border-collapse border mb-2">
                    <thead><tr className="bg-gray-200">
                      <th className="border p-2 text-left">Nombre</th>
                      <th className="border p-2 text-left">Stock Disponible</th>
                      <th className="border p-2 text-left">Alergeno</th>
                      <th className="border p-2 text-left">Cantidad</th>
                      <th className="border p-2 text-left">Opcional</th>
                      <th className="border p-2 text-left">Accion</th>
                    </tr></thead>
                    <tbody>
                      {selectedIngredientes.map((i) => {
                        const ingFull = allIngs.find(ai => ai.id === i.id);
                        return (
                        <tr key={i.id}>
                          <td className="border p-2">
                            <button
                              type="button"
                              onClick={() => navigate(`/ingredientes?edit=${i.id}`)}
                              className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                              title={`Editar ingrediente "${i.nombre}"`}
                            >
                              {i.nombre}
                            </button>
                          </td>
                          <td className="border p-2 font-mono">{ingFull ? `${ingFull.stock_actual} ${ingFull.unidad_medida_simbolo ?? ""}` : "—"}</td>
                          <td className="border p-2">{i.es_alergeno ? "Si" : "No"}</td>
                          <td className="border p-2">
                            <div className="flex items-center gap-2">
                              <DecimalInput
                                value={i.cantidad}
                                onChange={(val) => {
                                  setSelectedIngredientes(prev => prev.map(si =>
                                    si.id === i.id ? { ...si, cantidad: val } : si
                                  ));
                                }}
                                min={0.01} step={0.01}
                                decimals={2}
                                className="w-24"
                              />
                               <select
                                 value={i.unidad_medida_id ?? ''}
                                 onChange={(e) => {
                                   const newUnitId = e.target.value ? Number(e.target.value) : null;
                                   setSelectedIngredientes(prev => prev.map(si => {
                                     if (si.id !== i.id) return si;
                                     const oldUnitId = si.unidad_medida_id;
                                     // Auto-convert quantity when unit changes
                                     const newCant = oldUnitId && newUnitId
                                       ? convertirCantidad(si.cantidad, oldUnitId, newUnitId, factores)
                                       : si.cantidad;
                                     return { ...si, cantidad: newCant, unidad_medida_id: newUnitId };
                                   }));
                                 }}
                                 className="border rounded p-1 text-sm"
                               >
                                 <option value="">unidad/es</option>
                                  {unidades.filter(u => {
                                    // Filter by the ingredient's own unidad tipo, not the PI's selected unit
                                    const ingUnidad = ingFull ? unidades.find(un => un.id === ingFull.unidad_medida_id) : undefined;
                                    return !ingUnidad || u.tipo === ingUnidad.tipo;
                                  }).map(u => (
                                   <option key={u.id} value={u.id}>{u.simbolo}</option>
                                 ))}
                               </select>
                            </div>
                          </td>
                          <td className="border p-2 text-center">
                            <input
                              type="checkbox"
                              checked={i.es_removible}
                              onChange={(e) => {
                                setSelectedIngredientes(prev => prev.map(si =>
                                  si.id === i.id ? { ...si, es_removible: e.target.checked } : si
                                ));
                              }}
                              className="w-4 h-4 cursor-pointer"
                            />
                          </td>
                          <td className="border p-2">
                            <button type="button" onClick={() => setSelectedIngredientes(prev => prev.filter(si => si.id !== i.id))} className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer">Quitar</button>
                          </td>
                        </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
                <button type="button" onClick={() => setShowIngredienteSelector(true)}
                  className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">Seleccionar Ingredientes</button>
              </div>
              )}
            </>
          )}

          {/* ── Form-level validation error banner ── */}
          {formError && (
            <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded text-sm font-medium">
              {formError}
            </div>
          )}

          <div className="mt-4">
            <FormFooter
              isSubmitting={form.state.isSubmitting}
              isEditing={!!editingId}
              onCancel={handleCloseForm}
              updateLabel={stockEditOnly ? "Actualizar Stock" : undefined}
            />
          </div>
        </form>
      )}

      {/* Product list table via DataTable */}
      <DataTable
        columns={columns}
        data={items}
        total={total}
        skip={skip}
        limit={limit}
        onPageChange={handlePageChange}
        onLimitChange={handleLimitChange}
        isLoading={isLoading}
        sortBy={sortBy}
        sortOrder={sortOrder}
        onSort={handleSort}
        getRowClassName={(p: Producto) => (!p.disponible || p.stock_cantidad <= 0) ? "bg-gray-200" : undefined}
      />

      {/* Extra actions below table */}
      <div className="flex gap-2 mt-4 items-center justify-between">
        <div />
        {role === 'client' && (
          <button
            onClick={() => navigate("/carrito")}
            className="bg-green-700 text-white px-4 py-1.5 rounded text-sm font-semibold hover:bg-green-800 cursor-pointer"
          >
            Ver Carrito {useCartStore.getState().getItemCount() > 0 ? `(${useCartStore.getState().getItemCount()})` : ""}
          </button>
        )}
      </div>


      {showCategoriaSelector && (
        <CategoriaTreeSelector
          open={true}
          selectedIds={selectedCategorias.map(c => c.id)}
          onSelect={(ids) => {
            const selectedCats = findCategoriesInTree(categoriaTree, ids);
            setSelectedCategorias(selectedCats);
          }}
          onClose={() => setShowCategoriaSelector(false)}
        />
      )}

      {showIngredienteSelector && !form.getFieldValue('es_producto_terminado') && (
        <IngredienteSearchSelector
          open={true}
          allIngredientes={allIngs}
          unidades={unidades}
          factores={factores}
          selected={selectedIngredientes.map(i => ({ id: i.id, cantidad: i.cantidad, unidad_medida_id: i.unidad_medida_id }))}
          onSelect={(items) => {
            const selectedIngs = items.map(item => {
              const ing = allIngs.find(i => i.id === item.id);
              // Preserve es_removible from previous selection, default to true for new
              const prev = selectedIngredientes.find(si => si.id === item.id);
              const esRemovible = prev?.es_removible ?? true;
              return {
                id: item.id,
                nombre: ing?.nombre ?? '',
                es_alergeno: ing?.es_alergeno ?? false,
                cantidad: item.cantidad ?? 1,
                unidad_medida_id: item.unidad_medida_id ?? null,
                es_removible: esRemovible,
              };
            });
            setSelectedIngredientes(selectedIngs);
          }}
          onClose={() => setShowIngredienteSelector(false)}
        />
      )}

      {/* ── Stock Detail Modal: shows limiting ingredients ── */}
      <Modal open={!!showStockDetail} onClose={() => setShowStockDetail(null)} title={`Stock de "${showStockDetail?.nombre ?? ''}"`}>
        {stockDetailLoading ? (
          <p className="text-gray-500 text-sm text-center py-8">Cargando...</p>
        ) : stockDetailData.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-8">
            Este producto no tiene ingredientes asignados.
          </p>
        ) : (
          <>
            <p className="text-sm text-gray-600 mb-3">
              Para producir <strong>1 unidad</strong> de este producto, se necesita stock suficiente de cada ingrediente.
              Los ingredientes marcados en <span className="text-red-600 font-medium">rojo</span> son los que estan limitando la produccion.
            </p>
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b text-left text-gray-500 text-xs uppercase">
                  <th className="py-2 pr-2">Ingrediente</th>
                  <th className="py-2 px-2 text-right">Stock actual</th>
                  <th className="py-2 px-2 text-right">Necesario p/unidad</th>
                  <th className="py-2 px-2 text-right">Alcanza para</th>
                  <th className="py-2 pl-2 text-right">Faltante</th>
                  <th className="py-2 pl-2 text-center">Accion</th>
                </tr>
              </thead>
              <tbody>
                {stockDetailData.map((d) => (
                  <tr key={d.ingrediente_id} className={`border-b ${d.es_limitante ? 'bg-red-50' : ''}`}>
                    <td className={`py-2 pr-2 ${d.es_limitante ? 'text-red-700 font-medium' : ''}`}>
                      {d.ingrediente_nombre}
                      {d.es_limitante && <span className="ml-1 text-xs text-red-500">(limitante)</span>}
                    </td>
                    <td className="py-2 px-2 text-right font-mono">
                      {d.stock_actual} {d.unidad_medida_simbolo ?? ''}
                    </td>
                    <td className="py-2 px-2 text-right font-mono">
                      {d.cantidad_convertida} {d.unidad_medida_simbolo ?? ''}
                    </td>
                    <td className={`py-2 px-2 text-right font-mono ${d.producible === 0 ? 'text-red-600 font-semibold' : ''}`}>
                      {d.producible}
                    </td>
                    <td className={`py-2 pl-2 text-right font-mono ${d.deficit > 0 ? 'text-red-600' : 'text-gray-400'}`}>
                      {d.deficit > 0 ? `+${d.deficit}` : '--'}
                    </td>
                    <td className="py-2 pl-2 text-center">
                      <button
                        type="button"
                        onClick={() => navigate(`/ingredientes?edit=${d.ingrediente_id}`)}
                        className="text-xs bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700 cursor-pointer whitespace-nowrap"
                        title={`Editar ingrediente "${d.ingrediente_nombre}"`}
                      >
                        Editar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </Modal>

      {/* ── Delete confirmation dialog ── */}
      <ConfirmDialog
        open={crud.deleteConfirmOpen}
        title="Eliminar producto"
        message={`¿Esta seguro de eliminar '${crud.deleteTarget?.label ?? ''}'?`}
        variant="danger"
        confirmLabel="Eliminar"
        onConfirm={handleConfirmDelete}
        onCancel={crud.closeDeleteConfirm}
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
}
