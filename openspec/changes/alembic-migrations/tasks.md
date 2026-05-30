## 1. Inicialización de Alembic

- [x] 1.1 Ejecutar `alembic init migrations` desde `Backend/` (genera `alembic.ini` + `migrations/`)
- [x] 1.2 Configurar `alembic.ini`: apuntar `sqlalchemy.url` a la `DATABASE_URL` del .env (o usar `env.py` para leerla)
- [x] 1.3 Configurar `migrations/env.py` para que use `SQLModel.metadata` como `target_metadata`
- [x] 1.4 Configurar `env.py` para leer `DATABASE_URL` desde `python-dotenv` (como el resto de la app)
- [x] 1.5 Verificar que el autogenerate detecta todos los modelos importados en `main.py`

## 2. Migración inicial

- [x] 2.1 Generar migración inicial con `alembic revision --autogenerate -m "initial schema"`
- [x] 2.2 Revisar y corregir manualmente el script generado (autogenerate no siempre es perfecto)
- [x] 2.3 Probar `alembic upgrade head` en una DB vacía — debe crear todas las tablas
- [x] 2.4 Probar `alembic downgrade base` — debe eliminar todas las tablas

## 3. Integración con el startup de la app

- [x] 3.1 Reemplazar `SQLModel.metadata.create_all(engine)` en `main.py` por `alembic upgrade head` usando la API programática (`alembic.command.upgrade`)
- [x] 3.2 Verificar que el seed se ejecuta DESPUÉS de las migraciones (como hoy)
- [x] 3.3 Probar startup completo: migraciones + seed + app funcionando

## 4. Actualizar scripts existentes

- [x] 4.1 Actualizar `scripts/reset_db.py` para usar `alembic downgrade base` + `alembic upgrade head`
- [x] 4.2 Agregar comentario de deprecación a `scripts/run_migration.py` indicando usar `alembic revision --autogenerate`

## 5. Documentación

- [x] 5.1 Agregar sección en `README.md` o `Backend/README.md` con comandos básicos de Alembic:
  - `alembic revision --autogenerate -m "desc"`
  - `alembic upgrade head`
  - `alembic downgrade -1`
  - `alembic history`
