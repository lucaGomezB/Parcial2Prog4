/**
 * UnidadMedida types — TypeScript interfaces for measurement units.
 *
 * Aligns with backend schemas at Backend/modules/CatalogoDeProductos/UnidadMedida/schemas.py.
 */

/** Allowed measurement unit classification values. */
export type UnidadMedidaTipo = "masa" | "volumen" | "unidad" | "area";

/** A measurement unit as returned by the API (read model). */
export interface UnidadMedida {
  id: number;
  nombre: string;
  simbolo: string;
  tipo: UnidadMedidaTipo;
  factor_conversion: number;
  created_at: string;
}

/** Payload for creating a new measurement unit. */
export interface UnidadMedidaCreate {
  nombre: string;
  simbolo: string;
  tipo: UnidadMedidaTipo;
  factor_conversion: number;
}

/** Payload for updating an existing measurement unit. All fields optional. */
export interface UnidadMedidaUpdate {
  nombre?: string;
  simbolo?: string;
  tipo?: UnidadMedidaTipo;
  factor_conversion?: number;
}
