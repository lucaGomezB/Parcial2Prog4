## Context

El frontend actual (`CategoriasCRUD.tsx`) muestra las categorías en una tabla plana con paginación y un popup modal (`SubcategoriasPopup`) para ver las hijas de 1 nivel. El backend ya expone `GET /categorias/tree` que devuelve la jerarquía completa con N niveles de profundidad gracias a la relación `subcategorias` en el modelo `Categoria` y el schema `CategoriaTree` recursivo.

**Estado actual:**
- Tabla plana con paginación (10 items/página)
- `SubcategoriasPopup`: modal que solo muestra 1 nivel, sin acciones
- Filtro por padre mediante `<select>` + "Solo raíz"
- Lógica de jerarquía computada client-side con `allCats.filter()`
- Popup `ParentSelector` para elegir padre al crear/editar

## Goals / Non-Goals

**Goals:**
- Reemplazar la tabla plana por una **tabla árbol expandible/colapsable** inline
- Mostrar la jerarquía completa con indentación visual por nivel
- Soportar N niveles de profundidad (recursivo)
- Mantener todas las operaciones CRUD existentes (crear, editar, eliminar)
- Consumir `GET /categorias/tree` del backend en lugar de computar jerarquía en cliente
- Conservar filtro por nombre sobre la estructura tree

**Non-Goals:**
- No cambiar el backend (endpoint tree ya existe y funciona)
- No modificar el CRUD en sí (create/update/delete siguen igual)
- No agregar drag & drop para reordenar
- No agregar búsqueda full-text

## Decisions

### 1. Tree desde backend vs. tree computado en frontend
- **Decisión**: Usar `GET /categorias/tree` del backend.
- **Por qué**: Ya existe, devuelve la jerarquía completa con N niveles, y evita lógica de reconstrucción en frontend. El backend hace una sola query (lazy loading por relación SQLAlchemy) que para el volumen actual de datos es más que suficiente.

### 2. Componente tree recursivo vs. librería externa
- **Decisión**: Componente recursivo inline con estado local de expand/colapse (`useState<Set<number>>`).
- **Por qué**: No justifica agregar una dependencia (react-treebeard, react-accessible-treeview, etc.) para un árbol de ~8 nodos. El estado de expansión se maneja con un `Set<id>` sencillo.
- **Alternativa**: `react-accessible-treeview` — más accesible pero overkill para el caso de uso actual.

### 3. Paginación vs. carga completa
- **Decisión**: Carga completa del tree (sin paginación).
- **Por qué**: El volumen de categorías es bajo (docenas, no miles). Ya se cargaban todas via `getAll(0, 1000)` para el `allCats`. El tree endpoint devuelve todo igual.

### 4. Filtros en modo tree
- **Decisión**: El filtro por nombre oculta las ramas que no matchean, pero mantiene visibles los ancestros de un nodo filtrado (para no perder contexto jerárquico).
- **Por qué**: Si filtrás "Bebidas Frías", querés ver "Bebidas" como contexto, no solo el nodo aislado.

### 5. `ParentSelector` se mantiene
- **Decisión**: El popup para elegir padre al crear/editar se conserva como está, pero mostrando la lista jerárquica (con indentación) en lugar de plana.
- **Por qué**: Sigue siendo la UX más clara para seleccionar un padre.

### 6. Se elimina `SubcategoriasPopup`
- **Decisión**: Las subcategorías se ven inline en la tree table, el popup ya no tiene sentido.

## Risks / Trade-offs

- **[Rendimiento] Carga completa del tree**: Con el volumen actual (8 categorías) es insignificante. Si en el futuro hay cientos de categorías, considerar paginación server-side o lazy loading de hijos.
- **[UX] Tree profundo**: Si un día hay 6+ niveles, la indentación puede comprimir el texto. Mitigación: límite de indentación visual con `max pl-(N*4)` o scroll horizontal.
- **[Edición] Refresco del tree**: Después de crear/editar/eliminar, se recarga el tree completo. Es rápido pero podría optimizarse con actualización optimista si es necesario.
