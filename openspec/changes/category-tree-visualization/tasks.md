## 1. API Client

- [x] 1.1 Agregar método `getTree()` en `src/api/categorias.ts` que llame a `GET /categorias/tree` y retorne `CategoriaTree[]` — agregar también la interfaz `CategoriaTree` con `subcategorias: CategoriaTree[]`

## 2. Componente Tree Row Recursivo

- [x] 2.1 Crear componente `CategoryTreeRow` (inline en `CategoriasCRUD.tsx`) que reciba: `categoria: CategoriaTree`, `depth: number`, `expanded: Set<number>`, `onToggle: (id: number) => void`, y handlers de editar/eliminar
- [x] 2.2 Renderizar indentación visual mediante padding-left progresivo (`style={{ paddingLeft: ... }}`) usando el nivel de profundidad
- [x] 2.3 Renderizar icono de expandir/colapsar (+/−) cuando la categoría tenga `subcategorias.length > 0`. Si no tiene hijos, mostrar espacio vacío o placeholder no clickeable
- [x] 2.4 Renderizar las columnas: Nombre (con indentación), Descripción, Acciones (editar/eliminar)
- [x] 2.5 Renderizado recursivo: si la categoría está expandida, renderizar cada subcategoría llamando al mismo `CategoryTreeRow` con `depth + 1`

## 3. Refactor de CategoriasCRUD

- [x] 3.1 Reemplazar el estado `items: Categoria[]` (plano + paginado) por `treeData: CategoriaTree[]` (cargado desde `getTree()`)
- [x] 3.2 Agregar estado `expanded: Set<number>` para controlar qué nodos están expandidos
- [x] 3.3 Implementar función `toggleExpand(id: number)` que agregue/saque el id del Set
- [x] 3.4 Reemplazar el `tbody` de la tabla plana por renderizado recursivo de `CategoryTreeRow` para cada root en `treeData`
- [x] 3.5 Eliminar la paginación (ya no es necesaria con carga completa del tree)
- [x] 3.6 Eliminar el `<select>` de filtro por padre y el checkbox "Solo con hijos" — reemplazar por filtro por nombre que opere sobre la estructura tree
- [x] 3.7 Implementar `filterTree(nodes: CategoriaTree[], query: string): CategoriaTree[]` que retorne los nodos que matchean + sus ancestros
- [x] 3.8 Eliminar `useEffect` de `allCats` (`categoriasApi.getAll(0, 1000)`) y el estado `allCats` — ya no se necesita
- [x] 3.9 Eliminar el componente `SubcategoriasPopup` y su estado `subcatPopup`
- [x] 3.10 Después de cada operación CRUD (create/update/delete), refrescar el tree llamando a `getTree()`

## 4. ParentSelector Jerárquico

- [x] 4.1 Modificar `ParentSelector` para recibir `CategoriaTree[]` y mostrar las categorías en orden jerárquico con indentación por nivel
- [x] 4.2 Excluir la categoría actual y sus descendientes (no se puede elegir a sí misma ni a un hijo como padre)

## 5. Exportación a Excel

- [x] 5.1 Modificar el export a Excel para aplanar el tree (incluyendo nivel de profundidad) y exportar las categorías visibles
