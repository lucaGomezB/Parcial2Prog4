import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch, setToken, setUserInfo } from "../api/client";
import { useAuthStore } from "../store/authStore";
import {
  useAppForm,
  composeValidators,
  required,
  email,
  minLength,
} from "../hooks/useAppForm";

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
  roles: string[];
}

type Modo = "login" | "register";

type LoginFormValues = {
  email: string;
  password: string;
  confirmPassword: string;
  nombre: string;
  apellido: string;
  celular: string;
};

export default function Login({ onLogin }: { onLogin?: () => void }) {
  const [modo, setModo] = useState<Modo>("login");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  // ── Obtener user info después de login/register ──
  const finalizarAuth = async () => {
    const userInfo = await apiFetch<UserInfo>("/auth/me");
    setUserInfo(userInfo);
    onLogin?.();
    navigate("/");
  };

  const form = useAppForm<LoginFormValues>({
    defaultValues: {
      email: "",
      password: "",
      confirmPassword: "",
      nombre: "",
      apellido: "",
      celular: "",
    },
    onSubmit: async ({ value }) => {
      setError("");
      setIsLoading(true);

      try {
        if (modo === "login") {
          const response = await apiFetch<LoginResponse>("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email: value.email, password: value.password }),
          });

          setToken(response.access_token, response.expires_in);
          await finalizarAuth();
        } else {
          if (value.password !== value.confirmPassword) {
            setError("Las contraseñas no coinciden");
            return;
          }

          const response = await apiFetch<LoginResponse>("/auth/register", {
            method: "POST",
            body: JSON.stringify({
              nombre: value.nombre.trim(),
              apellido: value.apellido.trim(),
              email: value.email.trim(),
              celular: value.celular.trim() || null,
              password: value.password,
            }),
          });

          setToken(response.access_token, response.expires_in);
          await finalizarAuth();
        }
      } catch (err: unknown) {
        console.error("Auth error:", err);

        if (err instanceof TypeError && err.message === "Failed to fetch") {
          setError(
            modo === "login"
              ? "No se puede conectar con el servidor. Asegurate de que el backend esté corriendo (uvicorn)."
              : "No se puede conectar con el servidor."
          );
        } else if (err instanceof Error && err.message) {
          const axiosErr = err as unknown as { response?: { data?: Record<string, unknown> } };
          const responseData = axiosErr?.response?.data;
          if (responseData?.detail) {
            setError(String(responseData.detail));
          } else {
            setError(
              modo === "login"
                ? "Email o contraseña incorrectos"
                : "Error al crear la cuenta. Intenta con otro email."
            );
          }
        } else {
          setError(
            modo === "login"
              ? "Error inesperado. Revisa la consola para más detalles."
              : "Error inesperado. Revisa la consola."
          );
        }
      } finally {
        setIsLoading(false);
      }
    },
  });

  const handleGuestLogin = () => {
    useAuthStore.getState().setRoles([]);
    navigate("/productos");
  };

  const irALogin = () => {
    setModo("login");
    setError("");
  };

  const irARegister = () => {
    setModo("register");
    setError("");
  };

  const cambiarModo = () => {
    setModo(modo === "login" ? "register" : "login");
    setError("");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-96">
        {/* ── Tabs: Login | Register ── */}
        <div className="flex mb-6 border-b border-gray-200">
          <button
            onClick={irALogin}
            className={`flex-1 pb-2 text-center font-medium cursor-pointer transition-colors ${
              modo === "login"
                ? "text-blue-600 border-b-2 border-blue-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Iniciar Sesión
          </button>
          <button
            onClick={irARegister}
            className={`flex-1 pb-2 text-center font-medium cursor-pointer transition-colors ${
              modo === "register"
                ? "text-blue-600 border-b-2 border-blue-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Crear Cuenta
          </button>
        </div>

        <h1 className="text-xl font-bold mb-4 text-center text-gray-800">
          {modo === "login" ? "Iniciar Sesión" : "Crear Cuenta"}
        </h1>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded mb-4 text-sm text-center">
            {error}
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            e.stopPropagation();
            void form.handleSubmit();
          }}
          className="flex flex-col gap-4"
        >
          {/* ── Campos específicos de registro ── */}
          {modo === "register" && (
            <>
              <div className="flex gap-3">
                <form.Field
                  name="nombre"
                  validators={{ onChange: required() }}
                >
                  {(field) => (
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
                      <input
                        value={field.state.value}
                        onChange={(e) => field.handleChange(e.target.value)}
                        onBlur={field.handleBlur}
                        disabled={isLoading}
                        className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:border-blue-500"
                      />
                      {field.state.meta.errors.length > 0 && (
                        <em className="text-red-500 text-xs mt-1 block">{field.state.meta.errors.join(", ")}</em>
                      )}
                    </div>
                  )}
                </form.Field>
                <form.Field
                  name="apellido"
                  validators={{ onChange: required() }}
                >
                  {(field) => (
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Apellido</label>
                      <input
                        value={field.state.value}
                        onChange={(e) => field.handleChange(e.target.value)}
                        onBlur={field.handleBlur}
                        disabled={isLoading}
                        className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:border-blue-500"
                      />
                      {field.state.meta.errors.length > 0 && (
                        <em className="text-red-500 text-xs mt-1 block">{field.state.meta.errors.join(", ")}</em>
                      )}
                    </div>
                  )}
                </form.Field>
              </div>
              <form.Field
                name="celular"
                validators={{ onChange: required() }}
              >
                {(field) => (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Celular</label>
                    <input
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      onBlur={field.handleBlur}
                      disabled={isLoading}
                      className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:border-blue-500"
                    />
                    {field.state.meta.errors.length > 0 && (
                      <em className="text-red-500 text-xs mt-1 block">{field.state.meta.errors.join(", ")}</em>
                    )}
                  </div>
                )}
              </form.Field>
            </>
          )}

          <form.Field
            name="email"
            validators={{ onChange: composeValidators(required(), email()) }}
          >
            {(field) => (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder={modo === "login" ? "ej: client@email.com" : ""}
                  className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:border-blue-500"
                  disabled={isLoading}
                />
                {field.state.meta.errors.length > 0 && (
                  <em className="text-red-500 text-xs mt-1 block">{field.state.meta.errors.join(", ")}</em>
                )}
              </div>
            )}
          </form.Field>

          <form.Field
            name="password"
            validators={{ onChange: composeValidators(required(), minLength(6)) }}
          >
            {(field) => (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                    placeholder="••••••••"
                    className="w-full border border-gray-300 px-3 py-2 pr-10 rounded focus:outline-none focus:border-blue-500"
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
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                    )}
                  </button>
                </div>
                {field.state.meta.errors.length > 0 && (
                  <em className="text-red-500 text-xs mt-1 block">{field.state.meta.errors.join(", ")}</em>
                )}
              </div>
            )}
          </form.Field>

          {/* ── Confirmar contraseña (solo registro) ── */}
          {modo === "register" && (
            <form.Field
              name="confirmPassword"
              validators={{ onChange: required() }}
            >
              {(field) => (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Confirmar contraseña</label>
                  <input
                    type="password"
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                    disabled={isLoading}
                    className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:border-blue-500"
                  />
                  {field.state.meta.errors.length > 0 && (
                    <em className="text-red-500 text-xs mt-1 block">{field.state.meta.errors.join(", ")}</em>
                  )}
                </div>
              )}
            </form.Field>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded mt-2 transition-colors cursor-pointer disabled:bg-blue-400 disabled:cursor-not-allowed"
          >
            {isLoading
              ? modo === "login" ? "Iniciando..." : "Creando cuenta..."
              : modo === "login" ? "Entrar" : "Crear cuenta"}
          </button>
        </form>

        {/* ── Invitado + toggle ── */}
        <div className="mt-6 text-center space-y-3">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">
                {modo === "login" ? "O ingresar como invitado" : "¿Ya tenés cuenta?"}
              </span>
            </div>
          </div>
          {modo === "login" ? (
            <button
              onClick={handleGuestLogin}
              className="w-full bg-gray-100 hover:bg-gray-200 text-gray-800 font-medium py-2 px-4 border border-gray-300 rounded transition-colors cursor-pointer"
            >
              Ver Menú (Invitado)
            </button>
          ) : (
            <button
              onClick={cambiarModo}
              className="w-full text-blue-600 hover:text-blue-800 font-medium py-2 px-4 transition-colors cursor-pointer"
            >
              Iniciar sesión
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
