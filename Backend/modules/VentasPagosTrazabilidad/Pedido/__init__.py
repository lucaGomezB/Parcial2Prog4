# Pedido — Order sub-module
# Central entity of the Sales module. Contains order CRUD, the FSM-based
# state machine (PENDIENTE -> CONFIRMADO -> EN_PREP -> EN_CAMINO -> ENTREGADO),
# stock validation, and cancellation logic.
