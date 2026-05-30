## Why

Hoy las tablas se crean con `SQLModel.metadata.create_all(engine)` en cada startup. Esto no modifica tablas existentes si cambia un modelo — para eso hay scripts SQL sueltos (`run_migration.py`) que se ejecutan manualmente y no tienen versionado ni rollback. En equipo o producción es insostenible: no hay forma de saber en qué estado está cada ambiente ni cómo volver atrás si algo falla.

## What Changes

1. **Inicializar Alembic**: `alembic init migrations` con configuración para SQLModel + PostgreSQL
2. **Configurar autogenerate**: Env (`DATABASE_URL`), detectar modelos SQLModel, generar migraciones automáticas
3. **Migración inicial**: Reemplazar `SQLModel.metadata.create_all(engine)` por `alembic upgrade head`
4. **Seed data**: Mantener seed post-migración (solo datos, no schema)
5. **Documentar**: Comandos básicos para el equipo (`alembic revision --autogenerate`, `alembic upgrade`, `alembic downgrade`)

## Capabilities

### New Capabilities
- `database-migrations`: Sistema de migraciones versionadas con Alembic, autogenerate desde modelos SQLModel, upgrade/downgrade, integrado en el startup de la app.

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- **Backend/**: Archivos `alembic.ini` + `migrations/` con env.py y versions/
- **Backend/main.py**: Reemplazar `SQLModel.metadata.create_all(engine)` por `alembic upgrade head`
- **Backend/requirements.txt**: Alembic ya está, no hay cambios
- **Backend/scripts/reset_db.py**: Actualizar para usar `alembic downgrade base` + `alembic upgrade head`
- **Backend/scripts/run_migration.py**: Deprecar a favor de `alembic revision --autogenerate`
