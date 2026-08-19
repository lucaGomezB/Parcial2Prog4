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
 * Security note: The JWT access token is currently persisted to localStorage
 * for session survival across page reloads. This is a known trade-off: it
 * enables seamless refresh but is technically vulnerable to XSS. Future
 * iterations should consider keeping the token in memory only and relying
 * exclusively on the httpOnly refresh cookie for session restoration.
 * The refresh token itself is an httpOnly cookie managed entirely by the
 * backend, making it inaccessible to JavaScript.
 */
import axios, { AxiosError } from "axios";
import type { InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "@/shared/store/authStore";
import type { UserInfo } from "@/shared/types/auth";

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

/** Shape of the backend /auth/refresh response.
 *  The refresh token itself is set as an httpOnly cookie and never appears
 *  in the response body (XSS protection). */
interface RefreshResponse {
  access_token: string;
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
  timeout: 15_000,  // 15s timeout to prevent hanging requests on backend downtime
});

// ── Token Management (persisted to localStorage, survives page reload) ──

/** Clean up any legacy localStorage keys from previous versions. */
;(() => {
  localStorage.removeItem("authToken");
  localStorage.removeItem("userInfo");
  localStorage.removeItem("userRole");
})();

// ── Store accessors (for non-React modules) ──

/** Returns the current token info from the Zustand store, or null if not set. */
export function getToken(): TokenInfo | null {
  const { accessToken, expiresAt } = useAuthStore.getState();
  if (!accessToken || expiresAt === null) return null;
  return { accessToken, expiresAt: expiresAt as number };
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
 * Uses refreshToken() which internally calls axios directly (bypassing the
 * apiClient interceptor) to avoid a circular refresh loop.
 *
 * Called once during app bootstrap in App.tsx.
 *
 * @returns true if a new access token was obtained, false otherwise.
 */
export async function refreshSession(): Promise<boolean> {
  try {
    const data = await refreshToken();
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

// ── Refresh Lock: serializes concurrent refresh attempts via a promise-based lock ──

/**
 * When multiple callers request a token refresh simultaneously, only one
 * HTTP call is made. The others await the same promise and receive the
 * same result.
 *
 * A Promise reference replaces a boolean flag so the check-and-set is
 * atomic within the JS event loop, eliminating the race window where two
 * concurrent callers could both start duplicate /auth/refresh calls.
 */
let refreshPromise: Promise<RefreshResponse> | null = null;

/**
 * Atomically refreshes the access token via the httpOnly refresh cookie.
 *
 * Uses a promise-based lock so concurrent callers share a single backend
 * call. Called by: bootstrap refreshSession(), SessionTimeoutModal, and
 * the 401 response interceptor.
 */
export async function refreshToken(): Promise<RefreshResponse> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = axios
    .post<RefreshResponse>(
      `${BASE_URL}/auth/refresh`,
      {},
      { withCredentials: true }
    )
    .then((res) => res.data);

  try {
    const data = await refreshPromise;
    return data;
  } finally {
    refreshPromise = null;
  }
}

// ── Response Interceptor: auto-refresh on 401 ──

/**
 * On every response, if a 401 is received:
 *  1. Ignore if the failing request already retried, or if it targets an auth
 *     endpoint (/auth/refresh, /auth/logout, /auth/login, /auth/register).
 *  2. Call refreshToken() to obtain a new access token. The shared lock
 *     ensures only one backend call is made regardless of how many 401s
 *     arrive concurrently.
 *  3. On success, retry the original request. On failure, clear auth and reject.
 */
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Network errors (no response) — reject immediately, don't attempt refresh
    if (!error.response) {
      return Promise.reject(error);
    }

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (originalRequest.url?.includes("/auth/refresh") || originalRequest.url?.includes("/auth/logout") || originalRequest.url?.includes("/auth/login") || originalRequest.url?.includes("/auth/register")) {
      useAuthStore.getState().logout();
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      const data = await refreshToken();
      setToken(data.access_token, data.expires_in);
      originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
      return apiClient(originalRequest);
    } catch (refreshError) {
      useAuthStore.getState().logout();
      return Promise.reject(refreshError);
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
      validateStatus: () => true,
    });

    if (response.status === 401) {
      return { data: null, status: 401 };
    }

    return { data: response.data, status: response.status };
  } catch {
    return { data: null, status: 500 };
  }
}

/** Full paginated response shape returned by all list endpoints. */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

/**
 * Like apiFetch but extracts the `.items` array from a paginated backend response.
 *
 * All list endpoints in this project return the shape:
 *   { items: T[], total: number, skip: number, limit: number }
 *
 * This wrapper extracts the array so callers receive T[] directly,
 * with a runtime guard against non-array values from corrupted responses.
 */
export async function apiFetchPaginated<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T[]> {
  const data = await apiFetch<{ items: T[] } & Record<string, unknown>>(endpoint, options);
  return Array.isArray(data?.items) ? data.items : [];
}

/**
 * Like apiFetchPaginated but returns the full response including pagination
 * metadata (total, skip, limit) so consumers can render paginated UIs.
 */
export async function apiFetchPaginatedFull<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<PaginatedResponse<T>> {
  const data = await apiFetch<{ items: T[]; total?: number; skip?: number; limit?: number }>(endpoint, options);
  return {
    items: Array.isArray(data?.items) ? data.items : [],
    total: data?.total ?? 0,
    skip: data?.skip ?? 0,
    limit: data?.limit ?? 10,
  };
}
