/**
 * Axios HTTP client configuration and authentication utilities.
 *
 * This module provides:
 *  - A pre-configured Axios instance (`apiClient`) with a proxy-based base URL.
 *  - Request interceptor that attaches the JWT Bearer token to every request.
 *  - Response interceptor that catches 401 errors and automatically attempts
 *    a token refresh via the httpOnly refresh cookie, queuing concurrent requests
 *    so only one refresh call is made at a time.
 *  - Backward-compatible wrappers (`apiFetch`, `apiFetchOptional`) for modules
 *    that previously used the native Fetch API.
 *
 * Security note: The JWT access token is kept only in memory (Zustand store).
 * It is NEVER persisted to localStorage. The refresh token is an httpOnly cookie
 * managed entirely by the backend, making it inaccessible to JavaScript and
 * therefore immune to XSS-based theft.
 */
import axios, { AxiosError } from "axios";
import type { InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "../store/authStore";

/**
 * Base URL for all API requests.
 * In development, Vite proxies /api to the backend server via vite.config.ts.
 * In production, the same origin serves both frontend and backend.
 */
const BASE_URL = "/api";

// ── Types ──

/** Shape of the access token information kept in memory. */
interface TokenInfo {
  accessToken: string;
  expiresAt: number;
}

/** Public user profile returned by /auth/me. */
export interface UserInfo {
  id: number;
  nombre: string;
  apellido: string;
  email: string;
  celular?: string | null;
  roles: string[];
}

/** Shape of the backend /auth/refresh response. */
interface RefreshResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// ── Axios Instance ──

/**
 * Axios client shared by all API modules.
 *
 * withCredentials: true is required so that the httpOnly refresh cookie
 * is sent on every request (needed for the backend to identify the session).
 */
const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

// ── Token Management (in-memory only — never localStorage) ──

/** Clean up any legacy localStorage tokens on import (migration safeguard). */
;(() => {
  localStorage.removeItem("authToken");
  localStorage.removeItem("userInfo");
  localStorage.removeItem("userRole");
})();

// ── Store accessors (for non-React modules) ──

/** Returns the current token info from the Zustand store, or null if not set. */
export function getToken(): TokenInfo | null {
  const { accessToken, expiresAt } = useAuthStore.getState();
  if (!accessToken) return null;
  return { accessToken, expiresAt };
}

/** Persists a new access token and its expiry to the store. */
export function setToken(accessToken: string, expiresIn: number): void {
  useAuthStore.getState().setSession(accessToken, expiresIn);
}

/** Returns just the access token string, or null if not set. */
export function getAccessToken(): string | null {
  return useAuthStore.getState().accessToken;
}

/** Clears all authentication state (calls store.logout()). */
export function clearAuth(): void {
  useAuthStore.getState().logout();
}

/** Sets the full user info object in the store. */
export function setUserInfo(user: UserInfo): void {
  useAuthStore.getState().setUser(user);
}

/** Returns the current user info, or null if not authenticated. */
export function getUserInfo(): UserInfo | null {
  return useAuthStore.getState().user;
}

/** Returns the current user's roles array, or an empty array. */
export function getUserRoles(): string[] {
  const user = useAuthStore.getState().user;
  return user?.roles ?? [];
}

/**
 * Attempts to restore a session on page reload using the httpOnly refresh cookie.
 *
 * This function uses raw axios (not the apiClient instance) to avoid triggering
 * the response interceptor, which would cause a circular refresh loop.
 *
 * Called once during app bootstrap in App.tsx.
 *
 * @returns true if a new access token was obtained, false otherwise.
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

// ── Request Interceptor: attaches Bearer token ──

/**
 * Before every outgoing request, if an access token exists in memory,
 * attach it as an Authorization header.
 *
 * This is the single point where the JWT is injected, keeping the rest
 * of the codebase agnostic about authentication headers.
 */
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const accessToken = getAccessToken();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// ── Refresh Queue: coalesces concurrent requests while refreshing ──

/**
 * When multiple requests fail simultaneously with 401, only one refresh
 * call is made. The others are queued here and retried with the new token.
 */
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

/** Drains the queue, resolving or rejecting each pending request. */
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

// ── Response Interceptor: auto-refresh on 401, queue concurrent retries ──

/**
 * On every response, if a 401 is received:
 *  1. Ignore if the failing request already retried, or if it IS the refresh
 *     endpoint itself (to prevent infinite loops).
 *  2. If a refresh is already in progress, queue this request to retry later
 *     with the new token.
 *  3. Otherwise, attempt a single refresh call. On success, retry the original
 *     request and drain the queue. On failure, clear auth and reject everything.
 */
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (originalRequest.url?.includes("/auth/refresh") || originalRequest.url?.includes("/auth/logout")) {
      useAuthStore.getState().logout();
      return Promise.reject(error);
    }

    if (isRefreshing) {
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
      const { data } = await axios.post<RefreshResponse>(
        `${BASE_URL}/auth/refresh`,
        {},
        { withCredentials: true }
      );

      setToken(data.access_token, data.expires_in);
      processQueue(null, data.access_token);

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

// ── Backward compatibility wrappers (for legacy fetch-style modules) ──

/**
 * Wraps apiClient.request in a Fetch-like signature for modules that were
 * written against the old `apiFetch` API.
 *
 * Parses the optional JSON body from a string and delegates to Axios.
 *
 * @typeParam T - The expected response data type.
 * @param endpoint - API path (e.g., "/productos/").
 * @param options - Standard RequestInit options (method, body as JSON string, headers).
 * @returns The parsed response data.
 */
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

/**
 * Like apiFetch but returns a tuple of {data, status} instead of throwing.
 * Useful when the caller wants to handle specific status codes (e.g., 401)
 * without a try/catch.
 */
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
      validateStatus: (status) => true,
    });

    if (response.status === 401) {
      return { data: null, status: 401 };
    }

    return { data: response.data, status: response.status };
  } catch {
    return { data: null, status: 500 };
  }
}
