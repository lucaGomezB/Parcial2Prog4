## Why

Actualmente todos los formularios del frontend usan `useState`/`useReducer` con manejo manual de estado, validación inline, y sin tipado declarativo. Esto genera código repetitivo, propenso a errores, y difícil de mantener. TanStack Form proporciona un sistema declarativo, type-safe, con validación integrada, manejo de estados (touched/dirty/submitting), y render performance optimizado.

## What Changes

1. **Agregar dependencia** `@tanstack/react-form` al proyecto
2. **Crear hook personalizado** `useAppForm()` con configuración base compartida (validators, adapters, temas)
3. **Refactorizar formularios existentes** progresivamente para usar TanStack Form:
   - Formularios de creación/edición con alta densidad de campos (ProductosCRUD, CategoriasCRUD, IngredientesCRUD)
   - Modales con formularios (direcciones, usuarios)
   - Formularios de login/registro
4. **Estandarizar patrón de validación**: schema-based con Zod o validator nativo
5. **No breaking**: los formularios legacy conviven hasta que se migren. No se rompe nada existente.

## Capabilities

### New Capabilities
- `form-management`: Sistema unificado de manejo de formularios con TanStack Form, incluyendo hooks base, validación tipada, y patrones de render.

### Modified Capabilities
<!-- No existing specs to modify. This adds a new form management layer without changing existing behavior. -->

## Impact

- **Frontend/package.json**: Nueva dependencia `@tanstack/react-form` (+ opcional `zod` para validación schema-based)
- **Frontend/src**: Nuevo archivo `hooks/useAppForm.ts` con configuración base
- **Frontend/src/pages/**: Migración progresiva de formularios en ProductosCRUD, CategoriasCRUD, IngredientesCRUD, Carrito, DireccionesPage, AdminUsuariosPage, LoginConceptual
- **Frontend/src/components/**: Posible extracción de componentes de campo reutilizables (TextField, SelectField, etc.)
