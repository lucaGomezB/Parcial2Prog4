"""
run_migration.py  --  Legacy migration runner (pre-Alembic).

Applies a single ad-hoc migration: adds the "disponible" column to the
productomedida table and marks medidas with zero stock as unavailable.

NOTE: This script predates Alembic integration. All new migrations should
use Alembic via `alembic upgrade head`. Keep this file for reference only
in case the production database needs this specific migration applied
without going through Alembic.

Run with:
    python scripts/run_migration.py
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load connection string from .env at Backend/ root.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env")
    exit(1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Guard: skip the ALTER if the column was already added by a previous run.
    result = conn.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name='productomedida' AND column_name='disponible'")
    )
    if result.fetchone():
        print("Column 'disponible' already exists, skipping add.")
    else:
        # Add the boolean column; default TRUE means existing rows with stock > 0
        # are automatically marked as available.
        conn.execute(text("ALTER TABLE productomedida ADD COLUMN disponible BOOLEAN NOT NULL DEFAULT TRUE"))
        # Existing medidas with stock = 0 should be marked unavailable.
        conn.execute(text("UPDATE productomedida SET disponible = FALSE WHERE stock = 0"))
        conn.commit()
        print("Migration applied: added disponible column, set stock=0 medidas as not disponible.")

print("Done.")
