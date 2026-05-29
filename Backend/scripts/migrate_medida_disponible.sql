-- Migration: add disponible column to productomedida
ALTER TABLE productomedida ADD COLUMN disponible BOOLEAN NOT NULL DEFAULT TRUE;
