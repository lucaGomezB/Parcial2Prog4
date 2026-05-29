import { apiFetch } from "./client";

export interface DetallePedido {
  producto_id: number;
  cantidad: number;
  nombre_snapshot: string;
  precio_snapshot: string;
  subtotal_snap: string;
  medida_snapshot?: string | null;
  personalizacion?: number[] | null;
}

export interface UsuarioInfo {
  id: number;
  nombre: string;
  apellido: string;
  email: string;
}

export interface Pedido {
  id: number;
  usuario_id: number;
  direccion_id: number | null;
  estado_codigo: string;
  forma_pago_codigo: string;
  subtotal: string;
  descuento: string;
  costo_envio: string;
  total: string;
  notas: string | null;
  created_at: string;
  updated_at: string;
  detalles?: DetallePedido[];
  usuario?: UsuarioInfo | null;
}

export interface AvanzarResponse {
  id: number;
  estado_anterior: string;
  estado_actual: string;
  mensaje: string;
}

export interface CancelarResponse {
  id: number;
  estado_anterior: string;
  estado_actual: string;
  mensaje: string;
}

export interface StockInsuficienteDetalle {
  producto_id: number;
  nombre_producto: string;
  medida: string | null;
  cantidad_solicitada: number;
  stock_disponible: number;
}

export interface StockInsuficienteError {
  error: string;
  mensaje: string;
  detalles: StockInsuficienteDetalle[];
}

export interface CreatePedidoInput {
  usuario_id?: number;
  direccion_id?: number;
  forma_pago_codigo: string;
  subtotal: number;
  descuento?: number;
  costo_envio?: number;
  notas?: string;
  detalles: {
    producto_id: number;
    cantidad: number;
    nombre_snapshot: string;
    precio_snapshot: number;
    medida_id?: number | null;
  }[];
}

export const pedidosApi = {
  getActivos: (skip = 0, limit = 100) =>
    apiFetch<Pedido[]>(`/pedidos/activos?skip=${skip}&limit=${limit}`),

  getHistorial: (skip = 0, limit = 100) =>
    apiFetch<Pedido[]>(`/pedidos/historial?skip=${skip}&limit=${limit}`),

  getMisPedidos: (skip = 0, limit = 100) =>
    apiFetch<Pedido[]>(`/pedidos/mis-pedidos?skip=${skip}&limit=${limit}`),

  getById: (id: number) =>
    apiFetch<Pedido>(`/pedidos/${id}`),

  create: (data: CreatePedidoInput) =>
    apiFetch<Pedido>("/pedidos/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  avanzar: (id: number) =>
    apiFetch<AvanzarResponse>(`/pedidos/${id}/avanzar`, {
      method: "POST",
    }),

  cancelar: (id: number) =>
    apiFetch<CancelarResponse>(`/pedidos/${id}/cancelar`, {
      method: "POST",
    }),

  actualizarDetalle: (pedidoId: number, productoId: number, cantidad: number) =>
    apiFetch<Pedido>(`/pedidos/${pedidoId}/detalles/${productoId}`, {
      method: "PATCH",
      body: JSON.stringify({ cantidad }),
    }),
};
