## Context

Actualmente el frontend maneja formularios con `useState`/`useReducer` + elementos HTML nativos. No hay un patrón unificado:

- **Campos individuales**: `useState` por cada campo + `onChange` handler manual
- **Estados**: dirty/touched/submitting se manejan ad-hoc con flags booleanos
- **Validación**: inline en handlers o en submit, sin schema centralizado
- **Tipado**: los valores se castean manualmente al enviar

Esto funciona, pero escala mal. Cada formulario nuevo requiere reinventar la rueda.

## Goals / Non-Goals

**Goals:**
- Agregar TanStack Form como sistema de formularios estándar del proyecto
- Crear hook base `useAppForm()` con configuración compartida (validación, render, tipos)
- Migrar formularios existentes progresivamente
- Mantener convivencia con formularios legacy durante la migración

**Non-Goals:**
- No se migran todos los formularios en un solo cambio (se hace por tandas)
- No se cambia la lógica de negocio ni los schemas del backend
- No se agrega otra librería de validación (se usa el validator nativo de TanStack Form o Zod si se decide)

## Decisions

### 1. `@tanstack/react-form` vs React Hook Form vs Formik
- **Decisión**: TanStack Form.
- **Por qué**: Es la librería más moderna, con mejor soporte de TypeScript, render performance optimizado (sin re-renders innecesarios), y API declarativa. El equipo de TanStack tiene trayectoria sólida (React Query, Table, Router).
- **Alternativa**: React Hook Form (más popular, pero con wrapping de refs que complica componentes custom). Formik (más遗产, re-renders pesados).

### 2. Validación: Zod vs validator nativo
- **Decisión**: Usar el `validator` nativo de TanStack Form (funciones `fn`) inicialmente. Evaluar Zod como segunda iteración si se necesita schema-sharing con el backend.
- **Por qué**: El validator nativo es suficiente para la validación frontend (required, min, max, pattern). Zod agrega otra dependencia y solo es valioso si compartimos schemas con el backend (el backend usa Pydantic, no Zod).
- **Alternativa**: Zod + `@tanstack/zod-form-adapter` — más boilerplate inicial, pero útil si a futuro queremos tipado cross-stack.

### 3. Componentes de campo reutilizables
- **Decisión**: NO crear una librería de componentes de campo en este cambio.
- **Por qué**: El patrón actual usa componentes inline. Extraer TextField/SelectField genéricos requiere decisión de design system que no existe. Mejor mantener los campos inline con `useAppForm()` y refactorizar a componentes compartidos en un cambio futuro si se justifica.

### 4. Orden de migración
- **Decisión**: Migrar en este orden: (1) LoginConceptual (formulario chico, aislado), (2) DireccionesPage (mediano), (3) ProductosCRUD (grande, crítico), (4) AdminUsuariosPage y CategoriasCRUD/IngredientesCRUD, (5) Carrito (checkout).
- **Por qué**: De menor a mayor riesgo. Login es el más simple y autónomo.

### 5. `useAppForm()` hook base
- **Decisión**: Hook que envuelve `useForm` de TanStack con defaults del proyecto.
- **API**:
  ```ts
  function useAppForm<T extends Record<string, unknown>>(opts?: FormOptions<T>) {
    return useForm({
      ...opts,
      validators: { ... },
      // default behavior
    });
  }
  ```

## Risks / Trade-offs

- **[Riesgo] Regresión en formularios existentes**: Al migrar, algún campo podría tener comportamiento distinto. → **Mitigación**: Migrar de a un formulario por PR/tanda, con verificación visual y funcional.
- **[Riesgo] Curva de aprendizaje**: El equipo (o IA) debe aprender API de TanStack Form. → **Mitigación**: La API es intuitiva y bien documentada. El hook base abstrae la complejidad.
- **[Trade-off] Tamaño de bundle**: `@tanstack/react-form` agrega ~5KB gzip. Es negligible comparado con React 19.
- **[Trade-off] Sin Zod inicialmente**: Si más adelante se necesita validación cross-stack, hay que migrar los validators. Pero es preferible a agregar Zod prematuramente.

## Migration Plan

1. **Setup**: `npm install @tanstack/react-form`
2. **Crear** `src/hooks/useAppForm.ts` con configuración base
3. **Migrar LoginConceptual** como prueba de concepto
4. **Migrar DireccionesPage** (formulario de dirección)
5. **Migrar ProductosCRUD** (formulario grande con medidas, categorías, ingredientes)
6. **Migrar AdminUsuariosPage, CategoriasCRUD, IngredientesCRUD**
7. **Migrar Carrito** (checkout + modal dirección)
8. **Documentar** el patrón en `CONTRIBUTING.md` o archivo de conventions

## Open Questions

- ¿Usar `@tanstack/zod-form-adapter` desde el inicio o empezar con validator nativo?
- ¿Crear componentes de campo reutilizables (TextField, SelectField) ahora o después?
- ¿Migrar también los formularios de creación inline en modals o dejarlos para después?
