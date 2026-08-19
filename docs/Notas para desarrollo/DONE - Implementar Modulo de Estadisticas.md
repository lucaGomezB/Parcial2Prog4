un dashboard para gestionar el catálogo, stock, pedidos (con FSM y feed WebSocket) y usuarios desde un panel centralizado. El dashboard tendrá gráficos para ver las ventas por período, productos top, pedidods por estado e ingredientes más comprados (que más se les ha sumado stock), (los pedidos cancelados no deberán sumar) que usarán recharts, KPIs. Se alojará en app/modules/admin. El CRUD de Productos y Categorías contará con upload Cloudinary

El módulo de estadísticas solo proveerá KPIs y métricas del negocio exclusivamente al rol ADMIN. Todas las consultas son de solo lectura y se ejecutaran contra las tablas existentes del modelo (Pedido, DetallePedido, Producto y Pago). No requiere nuevas tablas ni migraciones adicionales. Los datos son consumidos por gráficos recharts del panel de administración. Los KPIs se calcularán en Service, Router será solo GET, sin lógica. Los schemas Pydantic serán ResumenResponse, VentasPeriodoItem, ProductoTopItem, PedidosEstadoItem e IngresosResponse.

Las queries clave del repository serán: 
- get_ventas_periodo(desde, hasta, agrupacion), con DATE_TRUNC de PostgreSQL. Las agrupaciones serán solo 'day', 'week' y 'month'. 
- get_productos_top(limit) (usará el snapshot del subtotal para los ingresos precisos). 
- get_pedidos_por_estado() que será un simple GROUP BY sobre el estado actual de cada pedido.
- get_resumen_kpis() (cada KPI es una query separada, el Service ensablará el ResumenResponse)
- get_ingresos_por_forma_pago(desde, hasta) (Solo pedidos con el pago aprobado. Forma de pago desde Pedido forma_pago_codigo).

El frontend verá KPIs Cards (StatCard Custom con 4 cards: ventas hoy, ticket promedio, pedidos activos y mes actual), Ingresos por forma de pago (BarChart horizontal), distribución por estado(PieChart + Pie), top productos (BarChart + Bar) y ventas por periodo (LineChart + Line).

Se debe verificar que los tests de integración validen que nunca se incluirán peididos con estado_codigo = CANCELADO en cálculos de ingresos o cantidades vendidas, Se usará subtotal_snap de DetallePedido para los ingresos por Producto (garantizando precios históricos correctos) y solo se contarán los pagos on mp_status='Approved' al calcular ingresos confirmados. Todos los montos devueltos deben ser DECIMAL (10,2), nunca float nativo Python para el dinero. y las queries de período aceptan desde y hasta como date (no datetime). El filtro usará IN BETWEEN.