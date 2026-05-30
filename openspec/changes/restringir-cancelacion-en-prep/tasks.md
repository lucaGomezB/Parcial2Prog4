## 1. Backend — Restringir cancelación en EN_PREP

- [x] 1.1 Modificar `PedidoService.cancelar_pedido` en `service.py`: reemplazar el umbral numérico por una lista explícita de estados permitidos para clientes (`{"PENDIENTE", "CONFIRMADO"}`)
- [x] 1.2 Actualizar el router (`router.py`) si es necesario: verificar que el endpoint `/cancelar` no tenga restricciones extras que entren en conflicto

## 2. Frontend — UI alignment

- [x] 2.1 Verificar que el botón "Cancelar" se oculte o deshabilite para clients en pedidos con estado EN_PREP
