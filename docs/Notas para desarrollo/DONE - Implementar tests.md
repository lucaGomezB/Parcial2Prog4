Usaremos tests con TestClient de FastAPI para tests de integración para los endpoints REST y WebSocket. Los tests cubrirán los flujos críticos (auntenticación, ciclo de vida de pedidos, pagos, estadísticas y WebSocket).

En el directorio tests/ vamos a tener lo siguiente:

1. conftesst.py con los siguientes features, para probar los fixtures globales:
- engine de scope session, para crear un motor SQLite en memoria para aplicar create_all(). 
- db_session (SQLAlchemy) limpia para cada test, que hace rollback automático al finalizar cada test.
- client (TestClient FastAPI) que sobreescribe la dependency get_db con db_session
- admin, client y pedidos _headers, que loguean a los usuarios con sus respectivos roles, retornando cookies.
- producto_factory, que creará un Producto con stock disponible en la BD de test.
- pedido_factory, que creará un Pedido en estado PENDIENTE con un DetallePedido, aceptando usuario_id y producto_id.

2. test_auth.py para probar: register OK, login OK, login credenciales inválidas (401), logout + revocación, rate limit (429)

3. test_pedidos.py para probar: crear pedido OK, stock insuficiente (400), avanzar estado válido, avanzar estado inválido (422), cancelar propio e historial append only

4. test_estadisticas.py para probar: resumen OK, ventas por período, productos top, pedidos por estado, ingresos (solo approved) y verificar que CANCELADO no sume.

## PATRONES DE TEST POR MÓDULO:

- Auth: Arrange para crear usuarios, con un POST /auth/login. Assert: status 200, access_token en body y refresh_token en body. Hay que verificar que el token sea válido, el tipo de token sea 'bearer' y que la expiración esté en expires_in.

- Pedidos FSM: Arrange para crear pedidos en PENDIENTE, el PATCH /pedidos/{id}/estado con CONFIRMADO, assert: 200, estado_codigo='CONFIRMADO'. Hay que verificar que las transiciones válidas actualicen el estado del historial append only, tendrá un nuevo registro!

- Pedidos FSM INVÁLIDO: Arrange para pedido en ENTREGADO (terminal), PATCH /pedidos/{id}/estado con EN_PREP, Assert 422. El estado terminal rechazará transiciones.

- Estadísticas: Arrange: Creará N pedidos con distintos estados y productos. Act: GET estadisticas/resumen. Assert: ventas_hoy > 0, CANCELADO excluido. Se debe verificar que los tests de integración validen que nunca se incluirán peididos con estado_codigo = CANCELADO en cálculos de ingresos o cantidades vendidas, Se usará subtotal_snap de DetallePedido para los ingresos por Producto (garantizando precios históricos correctos) y solo se contarán los pagos on mp_status='Approved' al calcular ingresos confirmados. Todos los montos devueltos deben ser DECIMAL (10,2), nunca float nativo Python para el dinero. y las queries de período aceptan desde y hasta como date (no datetime). El filtro usará IN BETWEEN.

- Deberán haber 5 tests por CADA módulo mínimamente.