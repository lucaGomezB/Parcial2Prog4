# Implementación de JWT - Sistema de Pedidos API

La implementación es completa y sigue las mejores prácticas. Aquí te explico cómo funciona:

---

## Backend (Python/FastAPI)

### 1. Configuración (`modules/IdentidadYAcceso/Auth/config.py`)

```python
# Carga SECRET_KEY desde .env
# Algoritmo: HS256
# Expiración: 30 minutos (configurable)

class Settings(BaseModel):
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
```

### 2. Schemas (`modules/IdentidadYAcceso/Auth/schemas.py`)

```python
LoginRequest    → { username, password }
TokenResponse   → { access_token, token_type, expires_in }
TokenData       → { user_id, username } (contenido del JWT)
```

### 3. Servicio (`modules/IdentidadYAcceso/Auth/service.py`)

- **`verify_password()`** → bcrypt para hashing (con fallback SHA256 legacy)
- **`create_access_token()`** → Codifica el token con `user_id`, `username`, `exp` y `iat`
- **`authenticate_user()`** → Busca usuario y verifica password

```python
def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: TokenData, expires_delta: timedelta | None = None) -> str:
    to_encode = data.model_dump()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

### 4. Dependencies (`modules/IdentidadYAcceso/Auth/dependencies.py`)

Dos dependencias FastAPI para proteger endpoints:

```python
# OBLIGATORIO: Requiere token válido
get_current_user = dependency → Lanza 401 si no hay token

# OPCIONAL: Retorna None si no hay token
get_current_user_optional = dependency → Útil para endpoints mixtos
```

```python
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> Usuario:
    if not credentials:
        raise HTTPException(status_code=401)

    payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    # ... valida y retorna el usuario
```

### 5. Router (`modules/IdentidadYAcceso/Auth/router.py`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/auth/login` | POST | Recibe credenciales → devuelve JWT |
| `/auth/me` | GET | Devuelve info del usuario (protegido) |
| `/auth/refresh` | POST | Renueva el token (protegido) |

---

## Frontend (React/TypeScript)

### 1. Cliente API (`Frontend/Primer-Parcial-Prog4/src/api/client.ts`)

```typescript
// Almacenamiento: localStorage (simula sessionStorage)
// Estructura: { accessToken, expiresAt }

// Función principal que incluye JWT en headers:
export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token?.accessToken) {
    headers["Authorization"] = `Bearer ${token.accessToken}`;
  }

  const res = await fetch(`${BASE_URL}${endpoint}`, {
    headers: { ...headers, ...options.headers },
    ...options,
  });

  // Si hay 401, limpiar auth y redirigir a login
  if (res.status === 401) {
    clearAuth();
    window.location.href = "/login";
    throw new Error("Sesión expirada");
  }

  return res.json();
}
```

### 2. Login (`Frontend/Primer-Parcial-Prog4/src/pages/LoginConceptual.tsx`)

```typescript
const handleLogin = async (e: React.FormEvent) => {
  // 1. POST /auth/login con { username, password }
  const response = await apiFetch<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

  // 2. Guarda token con setToken()
  setToken(response.access_token, response.expires_in);

  // 3. GET /auth/me para obtener user info
  const userInfo = await apiFetch<UserInfo>("/auth/me");
  setUserInfo(userInfo);

  // 4. Redirige a / o /productos
  navigate("/");
};
```

---

## Modelo de Usuario (`modules/IdentidadYAcceso/Usuario/models.py`)

```python
class Usuario(TimestampModel, SoftDeleteModel, table=True):
    __tablename__ = "usuario"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str = Field(unique=True)
    password_hash: str
    nombre_completo: str
    esta_activo: bool = Field(default=True)

    roles: List["Rol"] = Relationship(back_populates="usuarios", link_model=UsuarioRol)
```

---

## Dependencias necesarias

```txt
# Backend (requirements.txt)
python-jose[cryptography]  # JWT encoding/decoding
bcrypt                     # Password hashing
PyJWT                      # Alternativa a jose

# Frontend (ya integradas en fetch nativo)
# No se necesita ninguna librería extra
```

---

## Flujo completo

```
┌──────────┐     1. POST /auth/login      ┌──────────────┐
│  Login   │ ───────────────────────────► │   Backend    │
│   Page   │ ◄─────────────────────────── │              │
└──────────┘     JWT Token                │  Valida user │
                                        │  + bcrypt    │
                                           │  Retorna JWT │
                                           └──────────────┘
                                                │
                                                ▼
                        ┌─────────────────────────────────┐
                        │ localStorage.setItem("authToken",
                        │   { accessToken, expiresAt })
                        └─────────────────────────────────┘
                                                │
                                                ▼
                        ┌─────────────────────────────────┐
                        │ GET /auth/me (Bearer token)     │
                        │ → Devuelve user info            │
                        └─────────────────────────────────┘
```

---

## Seguridad a mejorar

1. **HTTPS** en producción (el token va en texto plano)
2. **Refresh tokens** (implementar token rotation)
3. **HttpOnly cookies** en vez de localStorage (más seguro contra XSS)
4. **Rate limiting** en `/auth/login` (prevenir brute force)

---

## Archivos relevantes

| Archivo | Descripción |
|---------|-------------|
| `Backend/modules/IdentidadYAcceso/Auth/config.py` | Configuración de JWT |
| `Backend/modules/IdentidadYAcceso/Auth/schemas.py` | Modelos de datos |
| `Backend/modules/IdentidadYAcceso/Auth/service.py` | Lógica de autenticación |
| `Backend/modules/IdentidadYAcceso/Auth/dependencies.py` | Dependencias FastAPI |
| `Backend/modules/IdentidadYAcceso/Auth/router.py` | Endpoints de autenticación |
| `Backend/modules/IdentidadYAcceso/Usuario/models.py` | Modelo de usuario |
| `Frontend/Primer-Parcial-Prog4/src/api/client.ts` | Cliente API con JWT |
| `Frontend/Primer-Parcial-Prog4/src/pages/LoginConceptual.tsx` | Página de login |