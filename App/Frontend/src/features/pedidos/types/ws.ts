/**
 * WebSocket event types for real-time order updates.
 *
 * Every WS event follows this schema:
 *   {
 *     event: "estado_cambiado" | "pedido_cancelado" | "pago_confirmado",
 *     pedido_id: number,
 *     estado_anterior: string | null,
 *     estado_nuevo: string,
 *     usuario_id: number | null,
 *     motivo: string | null,
 *     timestamp: string
 *   }
 */

export type WsEventType =
  | "estado_cambiado"
  | "pedido_cancelado"
  | "pago_confirmado";

export interface WsEvent {
  event: WsEventType;
  pedido_id: number;
  estado_anterior: string | null;
  estado_nuevo: string;
  usuario_id: number | null;
  motivo: string | null;
  timestamp: string;
}
