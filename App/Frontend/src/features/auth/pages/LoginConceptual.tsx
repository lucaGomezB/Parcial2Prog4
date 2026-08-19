import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiFetch, setToken, setUserInfo } from "@/shared/api/client";
import { AxiosError } from "axios";
import { useAuthStore } from "@/shared/store/authStore";
import { useCartStore } from "@/shared/store/cartStore";
import {
  useAppForm,
  composeValidators,
  required,
  email,
  minLength,
} from "@/shared/hooks/useAppForm";
import RegistrarForm from "@/features/auth/components/RegistrarForm";
import { formatValidationErrors } from "@/shared/utils/fieldLabels";

/**
 * Response shape from the backend auth endpoints (login/register).
 * Token is stored in localStorage via setToken() for subsequent API calls.
 */
interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

/**
 * Minimal user info returned by GET /auth/me after successful auth.
 */
interface UserInfo {
  id: number;
  nombre: string;
  apellido: string;
  email: string;
  celular?: string | null;
  roles: string[];
}

/** Discriminated union to toggle between login and register modes. */
type Modo = "login" | "register";

/** Form fields for login mode only. Registration uses RegistrarForm. */
interface LoginFormValues {
  email: string;
  password: string;
}

/**
 * LoginConceptual — Authentication page with login, register, and guest access.
 *
 * Manages two modes via a tab-like UI:
 *   - "login":    email + password only
 *   - "register": full form (nombre, apellido, celular, email, password, confirm)
 *
 * On success, stores the token via setToken() and fetches user info from /auth/me.
 * On failure, displays error messages parsed from the backend or network errors.
 *
 * @param onLogin - Optional callback invoked after successful authentication.
 */
export default function Login({ onLogin }: { onLogin?: () => void }) {
  const [searchParams] = useSearchParams();
  const initialMode: Modo = searchParams.get("mode") === "register" ? "register" : "login";
  const [modo, setModo] = useState<Modo>(initialMode);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  /**
   * Finalises authentication flow for LOGIN mode:
   *   1. Fetch the authenticated user's info from /auth/me.
   *   2. Persist it to the client-side store via setUserInfo().
   *   3. Invoke the parent's onLogin callback (if provided).
   *   4. Redirect based on role: ADMIN -> /admin/dashboard, others -> /
   */
  const finalizarAuth = async () => {
    const userInfo = await apiFetch<UserInfo>("/auth/me");
    setUserInfo(userInfo);
    useCartStore.getState().clearCarrito();
    onLogin?.();

    // Role-based redirect: ADMIN users go to the dashboard, others to home
    const roles = userInfo.roles ?? [];
    if (roles.includes("ADMIN")) {
      navigate("/admin/dashboard", { replace: true });
    } else {
      navigate("/", { replace: true });
    }
  };

  /**
   * Redirect handler for RegistrarForm.onSuccess.
   * RegistrarForm already fetched /auth/me and set user info — we just
   * need to invoke onLogin callback and redirect based on role.
   */
  const handleRegistroSuccess = () => {
    useCartStore.getState().clearCarrito();
    onLogin?.();
    const roles = useAuthStore.getState().user?.roles ?? [];
    if (roles.includes("ADMIN")) {
      navigate("/admin/dashboard", { replace: true });
    } else {
      navigate("/", { replace: true });
    }
  };

  /**
   * TanStack Form instance for the login form.
   *
   * On submit: POST /auth/login with email + password -> store token -> finalize.
   * Registration is handled entirely by RegistrarForm.
   *
   * Error handling covers:
   *   - Network failure (TypeError "Failed to fetch"): backend not running.
   *   - Backend validation errors (response.detail).
   *   - Generic fallback messages.
   */
  const form = useAppForm<LoginFormValues>({
    defaultValues: {
      email: "",
      password: "",
    },
    onSubmit: async ({ value }: { value: LoginFormValues }) => {
      setError("");
      setIsLoading(true);

      try {
        const response = await apiFetch<LoginResponse>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email: value.email, password: value.password }),
        });

        setToken(response.access_token, response.expires_in);
        await finalizarAuth();
      } catch (err: unknown) {
        console.error("Auth error:", err);

        let errorMsg = "";
        if (err instanceof AxiosError && err.response?.data) {
          const body = err.response.data as Record<string, unknown>;
          if (body.errors && Array.isArray(body.errors)) {
            const messages = formatValidationErrors(body.errors as Array<{ loc: string[]; msg: string; type: string }>);
            errorMsg = messages.join('\n');
          } else if (body.detail && typeof body.detail === "string") {
            errorMsg = body.detail;
          }
        }
        if (!errorMsg) {
          errorMsg = "No se pudo iniciar sesion. Verifique su email y contrasena.";
        }
        setError(errorMsg);
      } finally {
        setIsLoading(false);
      }
    },
  });

  /**
   * Guest login — sets an empty roles array so the app treats the user as
   * unauthenticated client, then navigates to the product listing.
   */
  const handleGuestLogin = () => {
    useAuthStore.getState().setRoles([]);
    useCartStore.getState().clearCarrito();
    navigate("/productos");
  };

  /** Switch to login tab and clear any previous errors. */
  const irALogin = () => {
    setModo("login");
    setError("");
  };

  /** Switch to register tab and clear any previous errors. */
  const irARegister = () => {
    setModo("register");
    setError("");
  };

  /**
   * Toggles between login and register modes.
   * Used by the hyperlink-style button below the form.
   */
  const cambiarModo = () => {
    setModo(modo === "login" ? "register" : "login");
    setError("");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded-lg shadow-md w-96">
        {/* Tab navigation: two buttons that switch between login and register modes. */}
        <div className="flex mb-6 border-b border-gray-200">
          <button
            onClick={irALogin}
            className={`flex-1 pb-2 text-center font-medium cursor-pointer transition-colors ${
              modo === "login"
                ? "text-blue-600 border-b-2 border-blue-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Iniciar Sesion
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

        {modo === "register" ? (
          <>
            <h1 className="text-xl font-bold mb-4 text-center text-gray-800">Crear Cuenta</h1>
            <RegistrarForm onSuccess={handleRegistroSuccess} />
          </>
        ) : (
          <>
            <h1 className="text-xl font-bold mb-4 text-center text-gray-800">Iniciar Sesion</h1>

            {/* Error banner — shown when login fails (network, validation, or credentials) */}
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
              {/* Email field */}
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
                      placeholder="ej: client@email.com"
                      className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:border-blue-500"
                      disabled={isLoading}
                    />
                    {field.state.meta.errors.length > 0 && (
                      <em className="text-red-500 text-xs mt-1 block">{field.state.meta.errors.join(", ")}</em>
                    )}
                  </div>
                )}
              </form.Field>

              {/* Password field with show/hide toggle icon */}
              <form.Field
                name="password"
                validators={{ onChange: composeValidators(required(), minLength(6)) }}
              >
                {(field) => (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Contrasena</label>
                    <div className="relative">
                      <input
                        type={showPassword ? "text" : "password"}
                        value={field.state.value}
                        onChange={(e) => field.handleChange(e.target.value)}
                        onBlur={field.handleBlur}
                        placeholder="********"
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
                          // Eye-off icon when password is visible
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                          </svg>
                        ) : (
                          // Eye icon when password is hidden
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

              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded mt-2 transition-colors cursor-pointer disabled:bg-blue-400 disabled:cursor-not-allowed"
              >
                {isLoading ? "Iniciando..." : "Entrar"}
              </button>
            </form>
          </>
        )}

        {/* Guest / toggle section — divider with guest button (login) or "already have account" link (register) */}
        <div className="mt-6 text-center space-y-3">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">
                {modo === "login" ? "O ingresar como invitado" : "Ya tenes cuenta?"}
              </span>
            </div>
          </div>
          {modo === "login" ? (
            <button
              onClick={handleGuestLogin}
              className="w-full bg-gray-100 hover:bg-gray-200 text-gray-800 font-medium py-2 px-4 border border-gray-300 rounded transition-colors cursor-pointer"
            >
              Ver Menu (Invitado)
            </button>
          ) : (
            <button
              onClick={cambiarModo}
              className="w-full text-blue-600 hover:text-blue-800 font-medium py-2 px-4 transition-colors cursor-pointer"
            >
              Iniciar sesion
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
