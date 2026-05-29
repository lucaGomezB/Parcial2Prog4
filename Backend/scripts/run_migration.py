"""
Migration: add disponible column to productomedida.
- Adds the column with default TRUE
- Sets existing medidas with stock = 0 as not disponible
Run with: python scripts/run_migration.py
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env")
    exit(1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Check if column already exists
    result = conn.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name='productomedida' AND column_name='disponible'")
    )
    if result.fetchone():
        print("Column 'disponible' already exists, skipping add.")
    else:
        conn.execute(text("ALTER TABLE productomedida ADD COLUMN disponible BOOLEAN NOT NULL DEFAULT TRUE"))
        # Existing medidas with stock > 0 stay disponible (default TRUE),
        # medidas with stock = 0 get disponible = FALSE
        conn.execute(text("UPDATE productomedida SET disponible = FALSE WHERE stock = 0"))
        conn.commit()
        print("Migration applied: added disponible column, set stock=0 medidas as not disponible.")

print("Done.")
