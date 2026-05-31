## 1. Setup

- [x] 1.1 Instalar `@tanstack/react-form` como dependencia
- [x] 1.2 Crear directorio `src/hooks/` si no existe

## 2. Hook base

- [x] 2.1 Crear `src/hooks/useAppForm.ts` con wrapper sobre `useForm` de TanStack Form
- [x] 2.2 Configurar validators base (required, min, max, email pattern)
- [x] 2.3 Definir tipos genéricos para formularios del proyecto

## 3. Migración: LoginConceptual

- [x] 3.1 Refactorizar formulario de login para usar `useAppForm()`
- [x] 3.2 Refactorizar formulario de registro para usar `useAppForm()`
- [x] 3.3 Verificar que submit, errores y estados funcionan igual

## 4. Migración: DireccionesPage

- [x] 4.1 Refactorizar `DireccionModal` (crear/editar) para usar `useAppForm()`
- [x] 4.2 Verificar validación de campos requeridos

## 5. Migración: ProductosCRUD

- [x] 5.1 Refactorizar formulario de creación de producto para usar `useAppForm()`
- [x] 5.2 Refactorizar formulario de edición para usar `useAppForm()`
- [x] 5.3 Manejar medidas dinámicas con FieldArray de TanStack Form (las medidas se eliminaron en change anterior, no aplica)
- [x] 5.4 Integrar selectores de categorías/ingredientes con el estado del form (categorias_ids e ingredientes se derivan de selected state en el onSubmit)

## 6. Migración: AdminUsuariosPage, CategoriasCRUD, IngredientesCRUD

- [x] 6.1 Refactorizar `EditarUsuarioModal` y `CrearUsuarioModal`
- [x] 6.2 Refactorizar formulario de categoría
- [x] 6.3 Refactorizar formulario de ingrediente

## 7. Migración: Carrito (checkout)

- [x] 7.1 Refactorizar `NuevaDireccionModal` del carrito para usar `useAppForm()`

## 8. Documentación

- [x] 8.1 Documentar el patrón de formularios en `src/hooks/README.md`
- [x] 8.2 Agregar ejemplo de uso de `useAppForm()` en el README con ejemplos de cada validator y patrón
