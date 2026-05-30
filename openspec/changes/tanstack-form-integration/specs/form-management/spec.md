## ADDED Requirements

### Requirement: Hook base useAppForm
El sistema DEBE proveer un hook `useAppForm()` que envuelva `useForm` de TanStack Form con configuración base del proyecto (validators, tipos, comportamiento por defecto).

#### Scenario: Hook exportado desde src/hooks/useAppForm.ts
- **WHEN** un componente importa `useAppForm` desde `src/hooks/useAppForm.ts`
- **THEN** obtiene una instancia de `useForm` preconfigurada con validación base y tipos del proyecto

#### Scenario: Hook acepta opciones override
- **WHEN** un componente pasa opciones a `useAppForm({ defaultValues: {...}, validators: {...} })`
- **THEN** las opciones se mergean con las defaults, dando prioridad a las del componente

### Requirement: Formularios migrados a TanStack Form
El sistema DEBE migrar progresivamente los formularios existentes a TanStack Form, manteniendo funcionalidad idéntica.

#### Scenario: LoginConceptual migrado primero
- **WHEN** el formulario de login/registro se renderiza
- **THEN** usa `useAppForm()` con campos tipados, validación en submit, y estado de submitting

#### Scenario: DireccionesPage migrado
- **WHEN** el formulario de crear/editar dirección se renderiza
- **THEN** usa `useAppForm()` con validación de campos requeridos (calle, ciudad)

#### Scenario: ProductosCRUD migrado
- **WHEN** el formulario de crear/editar producto se renderiza
- **THEN** usa `useAppForm()` manejando el estado complejo (medidas dinámicas, selector de categorías/ingredientes)

#### Scenario: Formularios legacy conviven sin conflicto
- **WHEN** un componente no migrado convive en la misma página que uno migrado
- **THEN** ambos funcionan independientemente sin errores ni conflictos de estado

### Requirement: Validación declarativa
El sistema DEBE soportar validación declarativa por campo y por formulario usando el sistema de validators de TanStack Form.

#### Scenario: Validación por campo en submit
- **WHEN** el usuario envía un formulario con un campo vacío marcado como required
- **THEN** el campo se marca como inválido y se muestra el mensaje de error correspondiente

#### Scenario: Validación asíncrona
- **WHEN** el formulario tiene un campo con validación asíncrona (ej: email único)
- **THEN** TanStack Form maneja el estado de validación (validating/invalid) y muestra feedback al usuario
