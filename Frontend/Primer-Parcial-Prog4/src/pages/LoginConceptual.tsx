import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch, setToken, setUserInfo, clearAuth } from "../api/client";

interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

interface UserInfo {
  id: number;
  nombre: string;
  apellido: string;
  email: string;
  celular?: string | null;
}

export default function Login({ onLogin }: { onLogin: (role: 'admin' | 'guest') => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const response = await apiFetch<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      // Store access_token (refresh_token se guarda como httpOnly cookie en el backend)
      setToken(response.access_token, response.expires_in);

      // Get user info
      const userInfo = await apiFetch<UserInfo>("/auth/me");
      setUserInfo(userInfo);

      // Admin role
      localStorage.setItem("userRole", "admin");

      onLogin('admin');
      navigate("/");
    } catch (err: unknown) {
      console.error("Login error:", err);

      if (err instanceof TypeError && err.message === "Failed to fetch") {
        setError("No se puede conectar con el servidor. Asegurate de que el backend esté corriendo (uvicorn).");
      } else if (err instanceof Error && err.message) {
        // Try to extract the detail from axios error response
        const axiosErr = err as Record<string, unknown>;
        const responseData = axiosErr?.response?.data as Record<string, unknown> | undefined;
        if (responseData?.detail) {
          setError(String(responseData.detail));
        } else {
          setError("Email o contraseña incorrectos");
        }
      } else {
        setError("Error inesperado. Revisa la consola para más detalles.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleGuestLogin = () => {
    clearAuth();
    localStorage.setItem("userRole", "guest");
    onLogin('guest');
    navigate("/productos");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-96">
        <h1 className="text-2xl font-bold mb-6 text-center text-gray-800">
          Iniciar Sesión
        </h1>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded mb-4 text-sm text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ej: client@email.com"
              className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:border-blue-500"
              required
              disabled={isLoading}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Contraseña
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full border border-gray-300 px-3 py-2 pr-10 rounded focus:outline-none focus:border-blue-500"
                required
                disabled={isLoading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                disabled={isLoading}
                className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-500 hover:text-gray-700 cursor-pointer"
                tabIndex={-1}
              >
                {showPassword ? (
                  /* Eye-slash icon */
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                  </svg>
                ) : (
                  /* Eye icon */
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                )}
              </button>
            </div>
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded mt-2 transition-colors cursor-pointer disabled:bg-blue-400 disabled:cursor-not-allowed"
          >
            {isLoading ? "Iniciando..." : "Entrar"}
          </button>
        </form>

        <div className="mt-6 text-center">
          <div className="relative mb-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">O ingresar como invitado</span>
            </div>
          </div>
          <button
            onClick={handleGuestLogin}
            className="w-full bg-gray-100 hover:bg-gray-200 text-gray-800 font-medium py-2 px-4 border border-gray-300 rounded transition-colors cursor-pointer"
          >
            Ver Menu (Invitado)
          </button>
        </div>
      </div>
    </div>
  );
}
