## MP BACKEND: 

Revisar que el .env tenga las variables para configurar el entorno.

Se debe crear una preferencia, registrar un pedido de cobro en MP antes del pago.

El usuario debe ser atendido luego de que completa el flujo de pago.

El estado del pedido debe ser consultado contra la API de MP, no de la URL que retorna.

Luego de todas las validaciones, el pedido se puede marcar como completado.

Las funciones que hablarán con MP serán la de Crear Preferencia, registrando el pedido de cbro en MP y obteniendo la URL de checkout, y la función Consultar Estado, que pregunta a MP el estado real y actualizado de un pago.

Las Operaciones de negocio (API) serán:

- Crear Pago: Inicia el registro del pago asociado al pedido en la BD

- Procesar Webhook: Maneja la notificación asíncrona de MP

- Confirmar Pago: Actualiza el pedido tras verificar la aprobación real.

La idea clave de la lógica de negocio es que nunca se llamará a MP de forma directa; siempre pasará por funciones intermedias.

Nunca se confiará en la URL de retorno, siempre se verificará.

Se confirmará mediante redirect y webhook:

- redirect se ejecutará apenas el suuario regrese del pago. Es la confirmación inmediata y visible

- webhook IPN funcionará porque MP notifica por su cuenta. Es el respaldo cuando el usuario cierra el navegador. Siempre debe repsonder 200 OK. MP bloquea a quien responde onc errores y deja de enviar notificaciones.

Cada intento de pago tendrá una clave única (idempotency_key) para evitar pagos duplicados si el suuario recarga la página.

La lógica de MP debe estar separada de la de negocio.

Básicamente, el backend orquestará, MP decidirá y el pedido reflejará la verdad.

El frontend pide, el backend registra la preferencia y redirige, la pasarela cobra y al volver, el backend verifica la fuente de verdad antes de dar nada por pagado.


## MP FRONTEND:


El backend siempre debe consultar directamente a la API de Mercado Pago para validar transacciones con pedido id y payment id 
(para que nadie pueda manipular la URL y llegar a la página de éxito sin pagar.).

Debemos tener un SuccessPage y FailurePage, que ayudarán al usuario a revisar / concretar su transacción respectivamente.

El frontend NUNCA manejará dinero ni tokens secretos. Solo crea el carrito, redirige a MP y verifica el resultado.
