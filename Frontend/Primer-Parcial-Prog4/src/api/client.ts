import axios, { AxiosError } from "axios";
import type { InternalAxiosRequestConfig } from "axios";

const BASE_URL = "/api";

// ── Types ──
interface TokenInfo {
  accessToken: string;
  expiresAt: number;
}

interface UserInfo {
  id: number;
  nombre: string;
  apellido: string;
  email: string;
  celular?: string | null;
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

// ── Token Management (solo access_token en localStorage) ──
function getToken(): TokenInfo | null {
  const tokenData = localStorage.getItem("authToken");
  if (!tokenData) return null;
  try {
    return JSON.parse(tokenData) as TokenInfo;
  } catch {
    return null;
  }
}

export function setToken(accessToken: string, expiresIn: number): void {
  localStorage.setItem(
    "authToken",
    JSON.stringify({
      accessToken,
      expiresAt: Date.now() + expiresIn * 1000,
    } as TokenInfo)
  );
}

export function getAccessToken(): string | null {
  const token = getToken();
  return token?.accessToken ?? null;
}

export function clearAuth(): void {
  localStorage.removeItem("authToken");
  localStorage.removeItem("userInfo");
  localStorage.removeItem("userRole");
}

export function setUserInfo(user: UserInfo): void {
  localStorage.setItem("userInfo", JSON.stringify(user));
}

export function getUserInfo(): UserInfo | null {
  const data = localStorage.getItem("userInfo");
  if (!data) return null;
  try {
    return JSON.parse(data) as UserInfo;
  } catch {
    return null;
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
      clearAuth();
      window.location.href = "/login";
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
      clearAuth();
      window.location.href = "/login";
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
