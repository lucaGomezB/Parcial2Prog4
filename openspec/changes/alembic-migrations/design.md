## Context

El proyecto usa SQLModel con PostgreSQL. Actualmente:

1. **Startup**: `SQLModel.metadata.create_all(engine)` — crea tablas si no existen, pero NO modifica las existentes
2. **Cambios estructurales**: Scripts SQL manuales en `scripts/run_migration.py`
3. **Reset**: `scripts/reset_db.py` hace DROP SCHEMA + recreate

No hay versionado de schema, no hay historial, no hay rollback.

## Goals / Non-Goals

**Goals:**
- Alembic configurado con autogenerate para SQLModel
- Migración inicial que replique el schema actual
- `alembic upgrade head` en el startup en vez de `create_all`
- Documentación de comandos básicos

**Non-Goals:**
- No se modifica el modelo de datos actual (solo se versiona lo que ya existe)
- No se cambia el seed ni la lógica de negocio
- No se dockeriza ni se cambia el deploy

## Decisions

### 1. Autogenerate con SQLModel
- **Decisión**: Configurar `env.py` para que Alembic detecte los modelos de SQLModel via `SQLModel.metadata`.
- **Por qué**: SQLModel extiende SQLAlchemy, su `metadata` es compatible con Alembic. No necesitamos importar cada modelo manualmente en `env.py`.
- **Implementación**: `target_metadata = SQLModel.metadata`

### 2. Ubicación de migrations
- **Decisión**: `Backend/migrations/` (dentro del proyecto).
- **Por qué**: Convención standard de Alembic. Separado de `scripts/` que tiene scripts ad-hoc.

### 3. Startup: create_all → alembic upgrade head
- **Decisión**: Reemplazar `SQLModel.metadata.create_all(engine)` por `alembic upgrade head` usando subprocess o la API programática de Alembic.
- **Por qué**: `upgrade head` aplica migraciones pendientes de forma idempotente. Es más seguro que `create_all`.
- **API programática** vs subprocess: Usar `alembic.command.upgrade()` desde el código, no subprocess (más limpio, misma conexión).

### 4. Estrategia de semillas (seed)
- **Decisión**: El seed se ejecuta DESPUÉS de las migraciones, como hoy. No se versiona en Alembic.
- **Por qué**: Los datos semilla son datos, no schema. Si se versionan en Alembic, cada cambio de seed requiere una migración nueva.

### 5. reset_db.py
- **Decisión**: Actualizar para usar `alembic downgrade base` + `alembic upgrade head` en vez de DROP SCHEMA.
- **Por qué**: Más rápido y consistente. DROP SCHEMA requiere recrear todo desde cero.

## Risks / Trade-offs

- **[Riesgo] Autogenerate no detecta todos los cambios**: Cambios como rename de tabla/columna no se detectan automáticamente. → **Mitigación**: Siempre revisar y editar la migración generada antes de aplicarla.
- **[Riesgo] Conflicto entre create_all y upgrade**: Si corre `create_all` después de configurar Alembic, puede crear tablas que Alembic no tiene versionadas. → **Mitigación**: Eliminar `create_all` del startup, reemplazar por `upgrade head`.
- **[Trade-off] Tiempo de startup**: `alembic upgrade head` es más lento que `create_all` (lee la tabla `alembic_version`). → Es negligible (~10ms).
