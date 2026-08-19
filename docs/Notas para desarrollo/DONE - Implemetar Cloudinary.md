## Cloudinary


Es básicamente una nube donde vamos a subir imagenes y se nos retornará una URL, con la cual consumiremos.


CREDENCIALES:


Vamos a usarlo para optimizar el performance de nuestro sitio, de forma personal, seremos desarrolladores que subirán imágenes, trabajando con Python.

Lo que nos importa es en la pestaña Dashboard: El cloud name y la pestaña de API KEYS (a la derecha). Vamos a usar una API KEY y API SECRET de Master Admin.

Al consumir, las imagenes se cargarán al apartado de ASSETS, donde se podrán manipular. 


BACKEND:


El modelo de imagen que vamos a usar consiste de los siguientes atributos:

__tablename__ = "images"
id: Optional[int]
public_id: str (que no va a ser PK, pero sí True, max_length = 500)
url: str (max_length = 1000)
filename: str (max_length = 255)
format: Optional[str] (max_length = 20)
width: Optional[int]
height: Optional[int]
bytes: Optional[int]
created_at: datetime (default_factory=datetime.utcnow (o lo que establecimos previamente para que sea todo uniforme, en realidad.))

El repository de Image va a tener el método init, get_all_ordered y get_by_public_id

El router va a tener GET, POST (upload, donde recibiremos la lista de imagenes) y DELETE exclusivamente.

El Service va a tener las credenciales, una lista de los tipos de imagen permitidos (jpeg, png, gif y webp, con tamaño máximo de 10 MB) y los métodos:
init, list_all, get_by_id y upload_many

Recordá usar UoW para gestionar transacciones a la BD y asegurar consistencia, NADA MÁS, no lo uses para llevar a cabo llamadas a la API, de eso se encargará Service.

Cloudinary solo usa public_id, no conoce las ids propias.

Recordá que tienen que haber validaciones y las mismas prácticas de seguridad que hemos implementado durante todo el proyecto, como protección de rutas, RBAC, etc...


FRONTEND:


Se muestra un mapa de las imagenes que se traen del Backend

Se pueden cargar imagenes mediante input de tipo file que pueda recibir incluso multiples elementos para mostrar un carrusel por tarjeta con cada imagen que haya 
cargado el admin para dicho producto. Además, se podrán eliminar algunos de los elementos.

useMutation se podrá usar para validar las queries.

Para comunicarnos con el backend, lo haremos mediante formData, porque los archivos como tales se cargarán mediante, por ejemplo: 

export sync function uploadImages(files: File[]): Promise<Image[]>{
 const formData = new FormData();
 for (const file of files){
  formData.append("files", file);
 }
 
 const res = await fetch('${API_URL}/api/v3/images/upload', {
  method: "POST",
  body: formData,
 });

 if (!res.ok){
  const err = await res.json().catch(() => ({detail: "Upload failed" }));
  throw new Error(err.detail ?? "Upload failed");
 }

 return res.json();
}