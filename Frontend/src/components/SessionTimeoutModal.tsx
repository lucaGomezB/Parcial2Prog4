import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";
import { getToken, setToken, clearAuth } from "../api/client";

const ADVERTENCIA_MS = 60_000; // Mostrar modal faltando 60s
const CTA_SEGUNDOS = 30;       // Cuenta regresiva de 30s

export default function SessionTimeoutModal() {
  const navigate = useNavigate();
  const [mostrar, setMostrar] = useState(false);
  const [segundos, setSegundos] = useState(CTA_SEGUNDOS);
  const [extendiendo, setExtendiendo] = useState(false);
  const autoCloseRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Cerrar sesión totalmente ──
  const cerrarSesion = useCallback(async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch { /* si falla, igual limpiamos */ }
    clearAuth();
    navigate("/login", { replace: true });
  }, [navigate]);

  // ── Extender sesión vía refresh ──
  const extenderSesion = useCallback(async () => {
    setExtendiendo(true);
    try {
      const { data } = await apiClient.post<{
        access_token: string;
        expires_in: number;
      }>("/auth/refresh");
      setToken(data.access_token, data.expires_in);
      setMostrar(false);
      setSegundos(CTA_SEGUNDOS);
    } catch {
      clearAuth();
      navigate("/login", { replace: true });
    } finally {
      setExtendiendo(false);
    }
  }, [navigate]);

  // ── Effect 1: Verificar expiración cada 10s ──
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
  }, [mostrar, cerrarSesion]); // ← SOLO limpia el interval de chequeo

  // ── Effect 2: Cuando el modal se muestra, arrancar cuenta regresiva + auto-close ──
  useEffect(() => {
    if (!mostrar) return;

    // Reset segundos cada vez que se abre el modal
    setSegundos(CTA_SEGUNDOS);

    // Cuenta regresiva cada 1s
    const intervalo = setInterval(() => {
      setSegundos((prev) => Math.max(0, prev - 1));
    }, 1000);

    // Auto-logout a los 30s
    autoCloseRef.current = setTimeout(() => {
      cerrarSesion();
    }, CTA_SEGUNDOS * 1000);

    return () => {
      clearInterval(intervalo);
      if (autoCloseRef.current) clearTimeout(autoCloseRef.current);
    };
  }, [mostrar, cerrarSesion]);

  if (!mostrar) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999]">
      <div className="bg-white rounded-lg p-6 w-full max-w-sm shadow-xl text-center">
        <h2 className="text-lg font-bold mb-2">Sesión próxima a expirar</h2>
        <p className="text-sm text-gray-600 mb-4">
          Tu sesión expirará en <strong>{segundos}</strong> segundos.
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={cerrarSesion}
            className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-100 cursor-pointer"
          >
            Cerrar sesión
          </button>
          <button
            onClick={extenderSesion}
            disabled={extendiendo}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 cursor-pointer"
          >
            {extendiendo ? "Extendiendo..." : "Extender sesión"}
          </button>
        </div>
      </div>
    </div>
  );
}
