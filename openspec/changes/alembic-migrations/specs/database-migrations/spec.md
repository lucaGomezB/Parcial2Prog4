## ADDED Requirements

### Requirement: Migraciones versionadas con Alembic
El sistema DEBE usar Alembic para gestionar migraciones de schema de base de datos, con versionado, autogenerate, upgrade y downgrade.

#### Scenario: Migración inicial replica el schema actual
- **WHEN** se ejecuta `alembic upgrade head` en una base de datos vacía
- **THEN** se crean todas las tablas del modelo actual (equivalente a `SQLModel.metadata.create_all`)

#### Scenario: Autogenerate detecta cambios en modelos
- **WHEN** un modelo Python se modifica (nueva columna, nuevo índice, nueva tabla)
- **THEN** `alembic revision --autogenerate -m "descripcion"` genera un script de migración con los cambios detectados

#### Scenario: Upgrade aplica migraciones pendientes
- **WHEN** se ejecuta `alembic upgrade head`
- **THEN** se aplican todas las migraciones pendientes en orden, y la tabla `alembic_version` refleja la revisión actual

#### Scenario: Downgrade revierte la última migración
- **WHEN** se ejecuta `alembic downgrade -1`
- **THEN** la última migración se revierte y la base de datos vuelve al estado anterior

### Requirement: Startup usa alembic upgrade head
El sistema DEBE ejecutar `alembic upgrade head` al iniciar la aplicación, en vez de `SQLModel.metadata.create_all`.

#### Scenario: Startup aplica migraciones pendientes
- **WHEN** la aplicación FastAPI inicia y hay migraciones pendientes
- **THEN** se ejecuta `alembic upgrade head` automáticamente antes de que el servidor acepte requests

#### Scenario: Startup no falla si ya está al día
- **WHEN** la aplicación inicia y la base de datos ya está en la última versión
- **THEN** `alembic upgrade head` no hace nada y la app arranca normalmente
