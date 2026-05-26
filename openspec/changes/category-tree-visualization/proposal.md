## Why

Las categorías del sistema son jerárquicas (padre → hijo → subhijo), pero la tabla del frontend las muestra como una lista plana donde las subcategorías solo se ven en un popup modal de 1 nivel. Esto dificulta la navegación visual del árbol de categorías, especialmente cuando hay múltiples niveles de anidamiento.

## What Changes

1. **Frontend — API client**: Agregar llamada a `GET /categorias/tree` para obtener la estructura anidada.
2. **Frontend — Tree table**: Reemplazar la tabla plana + popup `SubcategoriasPopup` por una **tabla árbol expandible/colapsable** inline, que muestre:
   - Categorías raíz en el nivel superior
   - Hijas indentadas debajo de su padre, dentro de la misma fila
   - Soporte recursivo para N niveles de profundidad
   - Iconos de expandir/colapsar (+/−) en categorías que tienen hijos
   - Acciones de editar/eliminar en cada fila
3. **Frontend — Limpieza**: Eliminar `SubcategoriasPopup` y lógica de `allCats` ya que el tree endpoint reemplaza ambos.
4. **Frontend — Filtros**: Reemplazar el filtro plano por padre + "Solo raíz" por un filtro por nombre que opere sobre la estructura tree.

## Capabilities

### New Capabilities
- `category-tree-ui`: Componente de tabla árbol para visualización jerárquica de categorías con expand/colapse, indentación recursiva, y operaciones CRUD sobre la estructura tree.

### Modified Capabilities
<!-- Sin cambios en specs existentes — solo frontend. -->

## Impact

- **Frontend**: `src/pages/CategoriasCRUD.tsx` se reescribe parcialmente (nuevo componente tree table, se elimina `SubcategoriasPopup`, se modifica lógica de filtros).
- **Frontend**: `src/api/categorias.ts` se agrega método `getTree()`.
- **Backend**: Sin cambios — el endpoint `GET /categorias/tree` ya existe y funciona correctamente con soporte recursivo N niveles.
