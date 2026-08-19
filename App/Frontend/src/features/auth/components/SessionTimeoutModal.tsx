/**
 * SessionTimeoutModal — Proactive session expiry warning overlay.
 *
 * This component continuously monitors the JWT token's expiration time.
 * When the remaining time drops below ADVERTENCIA_MS (60s), it displays
 * a centered modal with a 30-second countdown.
 *
 * The user has two options:
 *   1. "Extender sesion" — calls POST /auth/refresh to get a new token.
 *   2. "Cerrar sesion"   — logs out immediately via POST /auth/logout.
 *
 * If no action is taken within 30 seconds, auto-logout fires.
 *
 * Architecture notes:
 *   - A 10-second interval (setInterval) checks token expiry.
 *   - A 1-second interval updates the countdown UI while the modal is visible.
 *   - A 30-second setTimeout acts as a safety net for auto-logout.
 *   - useRef is used for the auto-close timer so it can be cleaned up.
 *   - cerrandoSesion ref prevents duplicate logout calls (guard pattern).
 */

import { useState, useEffect, useRef, useCallback } from "react";
import apiClient from "@/shared/api/client";
import { getToken, setToken, refreshToken } from "@/shared/api/client";
import { useAuthStore } from "@/shared/store/authStore";

/** Show the warning modal when 60 seconds or less remain before token expiry. */
const ADVERTENCIA_MS = 60_000;

/** Countdown duration shown in the modal (30 seconds, ticks down every 1s). */
const CTA_SEGUNDOS = 30;

export default function SessionTimeoutModal() {
  const [mostrar, setMostrar] = useState(false);
  const [segundos, setSegundos] = useState(CTA_SEGUNDOS);
  const [extendiendo, setExtendiendo] = useState(false);
  const autoCloseRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cerrandoSesion = useRef(false);

  /**
   * Fully logs out the user:
   *   1. POST /auth/logout (best-effort, errors are swallowed).
   *   2. Clears the auth store via logout().
   *   3. Hard-redirects to /login.
   *
   * The cerrandoSesion ref prevents concurrent execution (e.g., when
   * both the interval and the setTimeout fire at the same time).
   */
  const cerrarSesion = useCallback(async () => {
    if (cerrandoSesion.current) return;
    cerrandoSesion.current = true;
    try {
      await apiClient.post("/auth/logout");
    } catch { /* if logout fails we still clear locally */ }
    useAuthStore.getState().logout();
    window.location.href = "/login";
  }, []);

  /**
   * Extends the session by calling refreshToken() (shared lock).
   * On success, updates the stored token and hides the modal.
   * On failure (e.g., refresh token expired), falls through to cerrarSesion.
   */
  const extenderSesion = useCallback(async () => {
    setExtendiendo(true);
    try {
      const data = await refreshToken();
      setToken(data.access_token, data.expires_in);
      setMostrar(false);
      setSegundos(CTA_SEGUNDOS);
    } catch {
      cerrarSesion();
    } finally {
      setExtendiendo(false);
    }
  }, [cerrarSesion]);

  /**
   * Polls every 10 seconds to check token expiration.
   * If msRestantes <= 0, logs out immediately.
   * If msRestantes <= ADVERTENCIA_MS and the modal is not yet shown, shows it.
   *
   * Dependency on "mostrar" prevents re-showing the modal if it's already open.
   */
  useEffect(() => {
    const verificar = () => {
      const token = getToken();
      if (!token) return;

      const msRestantes = token.expiresAt - Date.now();

      if (msRestantes <= 0) {
        cerrarSesion();
        return;
      }

      if (msRestantes <= ADVERTENCIA_MS && !mostrar) {
        setMostrar(true);
        setSegundos(CTA_SEGUNDOS);
      }
    };

    verificar();
    const id = setInterval(verificar, 10_000);
    return () => clearInterval(id);
  }, [mostrar, cerrarSesion]);

  /**
   * When the modal opens, start a 1-second countdown and a 30-second
   * auto-logout timer. Both are cleaned up when the modal closes or
   * the component unmounts.
   */
  useEffect(() => {
    if (!mostrar) return;

    // Reset countdown each time the modal opens
    setSegundos(CTA_SEGUNDOS);

    // 1-second interval: decrement countdown, auto-logout at 0
    const intervalo = setInterval(() => {
      setSegundos((prev) => {
        if (prev <= 1) {
          cerrarSesion();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    // Safety net: auto-logout after 30 seconds regardless of countdown state
    autoCloseRef.current = setTimeout(() => {
      cerrarSesion();
    }, CTA_SEGUNDOS * 1000);

    return () => {
      clearInterval(intervalo);
      if (autoCloseRef.current) clearTimeout(autoCloseRef.current);
    };
  }, [mostrar, cerrarSesion]);

  if (!mostrar) return null;

  // Warning: session about to expire
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999]">
      <div className="bg-white rounded-lg p-6 w-full max-w-sm shadow-xl text-center">
        <h2 className="text-lg font-bold mb-2">Sesion proxima a expirar</h2>
        <p className="text-sm text-gray-600 mb-4">
          Tu sesion expirara en <strong>{segundos}</strong> segundos.
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={cerrarSesion}
            className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-100 cursor-pointer"
          >
            Cerrar sesion
          </button>
          <button
            onClick={extenderSesion}
            disabled={extendiendo}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 cursor-pointer"
          >
            {extendiendo ? "Extendiendo..." : "Extender sesion"}
          </button>
        </div>
      </div>
    </div>
  );
}
