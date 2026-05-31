import axios, { AxiosError } from "axios";
import type { InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "../store/authStore";

const BASE_URL = "/api";

// ── Types ──
interface TokenInfo {
  accessToken: string;
  expiresAt: number;
}

export interface UserInfo {
  id: number;
  nombre: string;
  apellido: string;
  email: string;
  celular?: string | null;
  roles: string[];
}

interface RefreshResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// ── Axios Instance ──
const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,  // Necesario para enviar cookies httpOnly
});

// ── Token Management (TODO en memoria — nada en localStorage) ──

// Limpieza migratoria: datos viejos de sesión en localStorage ya no se usan
// (la cookie httpOnly del refresh token es la única persistencia)
;(() => {
  localStorage.removeItem("authToken");
  localStorage.removeItem("userInfo");
  localStorage.removeItem("userRole");
})();

export function getToken(): TokenInfo | null {
  const { accessToken, expiresAt } = useAuthStore.getState();
  if (!accessToken) return null;
  return { accessToken, expiresAt };
}

export function setToken(accessToken: string, expiresIn: number): void {
  useAuthStore.getState().setSession(accessToken, expiresIn);
}

export function getAccessToken(): string | null {
  return useAuthStore.getState().accessToken;
}

export function clearAuth(): void {
  useAuthStore.getState().logout();
}

export function setUserInfo(user: UserInfo): void {
  useAuthStore.getState().setUser(user);
}

export function getUserInfo(): UserInfo | null {
  return useAuthStore.getState().user;
}

export function getUserRoles(): string[] {
  const user = useAuthStore.getState().user;
  return user?.roles ?? [];
}

/**
 * Intenta renovar la sesión al cargar la página usando la cookie httpOnly (refresh token).
 * Si funciona → setea accessToken en el store y retorna true.
 * Si falla → no hay sesión activa, retorna false.
 */
export async function refreshSession(): Promise<boolean> {
  try {
    const { data } = await axios.post<RefreshResponse>(
      `${BASE_URL}/auth/refresh`,
      {},
      { withCredentials: true }
    );
    useAuthStore.getState().setSession(data.access_token, data.expires_in);
    return true;
  } catch (err) {
    console.error('[auth] refresh failed:', err);
    return false;
  }
}

// ── Request Interceptor (adds Bearer token) ──
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const accessToken = getAccessToken();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// ── Refresh Queue ──
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null): void {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token!);
    }
  });
  failedQueue = [];
}

// ── Response Interceptor (401 → refresh via cookie → retry) ──
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    // Don't try to refresh if the failing request IS the refresh endpoint
    if (originalRequest.url?.includes("/auth/refresh")) {
      useAuthStore.getState().logout();
      return Promise.reject(error);
    }

    if (isRefreshing) {
      // Queue this request until refresh completes
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((newToken) => {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      // POST /auth/refresh SIN body — el refresh_token se envía automáticamente
      // desde la httpOnly cookie (withCredentials: true)
      const { data } = await axios.post<RefreshResponse>(
        `${BASE_URL}/auth/refresh`,
        {},
        { withCredentials: true }
      );

      // Store new access_token only (refresh_token está en la cookie)
      setToken(data.access_token, data.expires_in);

      // Process queued requests
      processQueue(null, data.access_token);

      // Retry original request
      originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
      return apiClient(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      useAuthStore.getState().logout();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default apiClient;

// ── Backward Compatibility: apiFetch wraps axios ──
// So existing API modules (categorias.ts, productos.ts, etc.) still work

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const method = options.method || "GET";
  const data = options.body ? JSON.parse(options.body as string) : undefined;

  const response = await apiClient.request<T>({
    url: endpoint,
    method,
    data,
    headers: options.headers as Record<string, string> | undefined,
  });

  return response.data;
}

export async function apiFetchOptional<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<{ data: T | null; status: number }> {
  try {
    const method = options.method || "GET";
    const data = options.body ? JSON.parse(options.body as string) : undefined;

    const response = await apiClient.request<T>({
      url: endpoint,
      method,
      data,
      headers: options.headers as Record<string, string> | undefined,
      validateStatus: (status) => true, // Don't throw on any status
    });

    if (response.status === 401) {
      return { data: null, status: 401 };
    }

    return { data: response.data, status: response.status };
  } catch {
    return { data: null, status: 500 };
  }
}
