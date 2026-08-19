## Websockets:


BACKEND 1:


HTTP: Patrón Pedido -> Respuesta. Cada petición abre y cierra una conexión, el servidor nunca habla primero. Funciona en base a Requests.

WebSockets son canales abiertos permanentes, cambian por completo cómo se diseñan las aplicaciones. El servidor y cliente se habblan cuando quieren. 
Full-duplex, mediante eventos.

Con concretar un handshake, se deja el canal abierto.

Contenidos del request del cliente:

// El cliente propone cambiar el protocolo
GET /ws HTTP/1.1
Host: api.ejemplo.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: ... // Sirve para verificar que el servidor entiende WS
Sec-WebSocket-Version: 13

Contenidos de la respuesta del servidor:

//El servidor responde 101 (NO 200). Después de esta linea, el protocolo HTTP deja de existir en esa conexión.
HTTP/1.1 101 Switching Protocols
Upgrade: sebsocket
Connection: Upgrade
Sec-WebSocket-Accept: ...

Para implementar WebSocket, seguiremos usando FastAPI, con @app.websocket y la clase WebSocket, junto con 3 operaciones clave: 
- accept()
- receive_* = receive_text() para strings | receive_json() para objetos, bloqueando hasta recibir algo. | 
- send_*() = send_text() para strings | send_json() para objetos, empujando datos al cliente.

Connection Manager:

Un endpoint solo puede hablar con un cliente a la vez. Para notificar a muchos, necesitamos un objeto que administre todas las conexiones activas y sepa cómo hacer 
broadcast. Este patrón es la base de cualquier sistema en tiempo real. Tiene los métodos __init__, conntect, disconnect y broadcast. Funciona para un grupo, sin filtrar.

Rooms; Canales con Nombre:

Cada conexion se une solo a los canales que le importan. Lo podemos implementar con dict y métodos join, leave y send_to_room.

2 Estrategias de Rooms:

El sistema usará ambas estrategias combinadas; rooms por rol para notificar equipos completos y rooms por entidad para notificar a un cliente específico sobre su propio pedido.

Ejemplos:

Por rol -> role:cocina (nombre de room) -> Todos los cocineros autenticados se podrán unir -> Se usará para notificar a un equipo completo.

Por entidad -> order:42 (nombre de room) -> Se unirá el cliente dueño del pedido 42 -> Se notificará solo al afectado.

RBAC aplicado a WebSockets:

Una vez validado el JWT, el sistema conoce el rol de usuario. Dicho rol se usa para decidir a qué roomms se puede unir y a cuáles se le prohibe el acceso. El control de acceso
se aplica en el momento de la conexión, no en cada mensaje. Los rooms se asignan al conectar.

WebSockets avisan cuando algo cambia, directamente nos pusheará, no hay polling.

La subscripción selectiva es cuando el cliente elige a qué pedidos escuchar, siempre cuando el Backend verifique que tenga permiso. 

Al caerse las conexiones, los rooms deben limpiarse para no intentar mandar mensajes a sockets muertos.


BACKEND 2:


Core/ deberá contar con websocket.py, que tendrá un ConnectionManager:

__init__ tendrá self.rooms y self.socket_rooms, unos diccionarios. Son inversos del otro, self.rooms responde a quienes están en los rooms y socket_rooms a en qué rooms está el socket.

Cuando un socket se desconecta, necesitamos sacarlo de todas las rooms.

Métodos clave del Connection Manager:

- connect(): Acepta los handshake y los une a las salas a partir de sus roles.

- disconnect(): Va limpiendo los rooms eliminando el mapa inverso, removiendo de cada room.

- join_order_room(): Va subscribiendo los clientes a los rooms de un pedido específico.

- leave_order_room(): Desuscribe los clientes que ya no usarán más ese room.

- broadcast, broadcasts a roles, broadcasts a pedidos, etc...

broadcast tendrá send_to(connection) no enviar 2 veces al mismo socket. Esto es importante, para que si un admin está en 2 salas (admin y pedidos), no reciba el evento duplicado. 

- utilidades de debug (contar conexiones, salas, etc...)

- métodos privados (para meter sockets a rooms o rooms a sockets, emitir a salas, etc..)

- Al final de todo, tendremos una instancia global (SOLO 1 EN TODA LA APP) 

En el módulo de Pedidos, en el router, vamos a tener los distintos endpoints y al final tendremos el de websocket: 

@router.websocket("/cocina/ws")
async def websocket_endpoint(websocket: WebSocket,):
... // validaciones de seguridad (que el token exista, el payload esté cargado, tenga nombre de usuario, el usuario exista, no esté deshabilitado, etc...), se une a las rooms, 
... // try ... except ... con un bucle infinito que mantendrá los mensajes con await websocket.receive_text(), parseo de JSON, subscripción a distintos pedidos, validaciones, agregación a salas, envio de JSON, etc...
// Los except tendrán las 2 salidas: WebSocketDisconnect y Exception, con manager.disconnect(websocket).

FRONTEND:

El WebSocket no reemplazará la API REST, solo la complementará. Tendremos rooms por cada Rol.

Vamos a usar un hook useWebSocket, donde manejaremos las funciones del WebSocket. Por ejemplo, podríamos tener un enabled para is authenticated, sino se desubscribe y así. SI está autorizado, se puede conectar y sigue el flujo lógico.

También tendremos un método closeCleanly, que le agrega un evento (listener) que verifica si el WS está abierto cuando llegue el evento open y que lo cierre con el evento 1000, en cambio, si ya estaba abierto, lo cerrará con el evento 1000.

Otra función connect, hará que si se cancela, hará un return, sino, hará una nueva instancia del WS y le pasará la URL del WS. Una vez esté conectado, se le asignará a la variable currentWs y también a la referencia.

Se pueden agregar eventos al socket, por ejemplo, onOpen nos dirá si el WS ya está abierto y conectado con bidireccionalidad. Guarda mensaje.ref y el evento WS_CONNECTED con data: null, reseteando el contador de reintentos por si se llega a caer.

Otros métodos son onMessage, onError (prácticamente toda la lógca la manejará onClose en realidad), onClose (lógica de desconexión, con un retry exponencial de retry con límite basándonos en el tipo de resultado por ejemplo (1000, 1008, etc...)), subscribirnos al pedido, etc...

Hay que hacer una prueba al levantar un nuevo pedido en la que se tengan 3 ventanas abiertas en simultaneo, donde se muestran los pasos del pedido para demostrar que funciona todo esto, a la hora de realizar el video.