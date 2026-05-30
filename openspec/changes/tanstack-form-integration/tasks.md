## 1. Setup

- [ ] 1.1 Instalar `@tanstack/react-form` como dependencia
- [ ] 1.2 Crear directorio `src/hooks/` si no existe

## 2. Hook base

- [ ] 2.1 Crear `src/hooks/useAppForm.ts` con wrapper sobre `useForm` de TanStack Form
- [ ] 2.2 Configurar validators base (required, min, max, email pattern)
- [ ] 2.3 Definir tipos genéricos para formularios del proyecto

## 3. Migración: LoginConceptual

- [ ] 3.1 Refactorizar formulario de login para usar `useAppForm()`
- [ ] 3.2 Refactorizar formulario de registro para usar `useAppForm()`
- [ ] 3.3 Verificar que submit, errores y estados funcionan igual

## 4. Migración: DireccionesPage

- [ ] 4.1 Refactorizar `DireccionModal` (crear/editar) para usar `useAppForm()`
- [ ] 4.2 Verificar validación de campos requeridos

## 5. Migración: ProductosCRUD

- [ ] 5.1 Refactorizar formulario de creación de producto para usar `useAppForm()`
- [ ] 5.2 Refactorizar formulario de edición para usar `useAppForm()`
- [ ] 5.3 Manejar medidas dinámicas con FieldArray de TanStack Form
- [ ] 5.4 Integrar selectores de categorías/ingredientes con el estado del form

## 6. Migración: AdminUsuariosPage, CategoriasCRUD, IngredientesCRUD

- [ ] 6.1 Refactorizar `EditarUsuarioModal` y `CrearUsuarioModal`
- [ ] 6.2 Refactorizar formulario de categoría
- [ ] 6.3 Refactorizar formulario de ingrediente

## 7. Migración: Carrito (checkout)

- [ ] 7.1 Refactorizar `NuevaDireccionModal` del carrito para usar `useAppForm()`

## 8. Documentación

- [ ] 8.1 Documentar el patrón de formularios en guía del proyecto
- [ ] 8.2 Agregar ejemplo de uso de `useAppForm()` en comentario o README
