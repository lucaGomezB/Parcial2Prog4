/**
 * fieldLabels.ts — Centralized mapping of backend field IDs to Spanish labels
 * and validation error formatter for all application forms.
 *
 * When the backend returns Pydantic 422 validation errors, this module
 * transforms technical field IDs ("precio_base") and English error messages
 * ("ensure this value is greater than 0") into actionable Spanish messages
 * ("Precio Base debe ser mayor a 0").
 */

// ── Field label mapping ────────────────────────────────────────────────

/**
 * Maps backend Pydantic field IDs to human-readable Spanish labels.
 * Covers all forms: ProductosCRUD, IngredientesCRUD, CategoriasCRUD,
 * UnidadesMedida, AdminUsuarios, Direcciones, AdminFormasPago, Auth.
 */
export const FIELD_LABELS: Record<string, string> = {
  // ── ProductosCRUD (ProductoCreate / ProductoUpdate) ──
  nombre: "Nombre",
  descripcion: "Descripcion",
  receta: "Receta",
  precio_base: "Precio Base",
  precio_actual: "Precio de Venta",
  imagenes_url: "Imagenes",
  tiempo_prep_min: "Tiempo de Preparacion",
  disponible: "Disponible",
  es_producto_terminado: "Producto Terminado",
  stock_manual: "Stock Manual",
  stock_cantidad: "Stock Calculado",
  categorias_ids: "Categorias",
  categoria_principal_id: "Categoria Principal",
  ingredientes: "Ingredientes",
  unidad_medida_id: "Unidad de Medida",

  // ── IngredientesCRUD (IngredienteCreate / IngredienteUpdate) ──
  // nombre, descripcion already covered above
  es_alergeno: "Alergeno",
  // precio_actual already covered above (shared label)
  stock_actual: "Stock Actual",
  // unidad_medida_id already covered above

  // ── CategoriasCRUD (CategoriaCreate / CategoriaUpdate) ──
  // nombre, descripcion already covered above
  parent_id: "Categoria Padre",
  imagen_url: "Imagen",
  orden_display: "Orden",

  // ── UnidadesMedida (UnidadMedidaCreate / UnidadMedidaUpdate) ──
  // nombre already covered above
  simbolo: "Simbolo",
  tipo: "Tipo",
  factor_conversion: "Factor de Conversion",

  // ── AdminUsuarios (UsuarioCreate / UsuarioUpdate) ──
  // nombre already covered above
  apellido: "Apellido",
  email: "Email",
  celular: "Celular",
  password: "Contrasena",
  roles_codigos: "Rol",

  // ── Direcciones (DireccionEntregaCreate / DireccionEntregaUpdate) ──
  alias: "Alias",
  linea1: "Direccion",
  linea2: "Complemento",
  ciudad: "Ciudad",
  provincia: "Provincia",
  codigo_postal: "Codigo Postal",
  latitud: "Latitud",
  longitud: "Longitud",
  es_principal: "Principal",
  es_local: "Es Local",

  // ── AdminFormasPago (FormaPagoCreate / FormaPagoUpdate) ──
  codigo: "Codigo",
  // descripcion already covered above
  habilitado: "Habilitado",

  // ── Auth login / register ──
  // email, password already covered above
  confirmacion_password: "Confirmacion de Contrasena",
};

// ── Pydantic → Spanish message transformation ──────────────────────────

interface ErrorEntry {
  loc: string[];
  msg: string;
  type: string;
}

/**
 * Regex patterns that map Pydantic validation error messages to
 * actionable Spanish phrases. Each entry has a regex and a function
 * that produces the Spanish replacement from the matched groups.
 */
const PYTHON_MESSAGE_PATTERNS: Array<{
  regex: RegExp;
  translate: (match: RegExpMatchArray) => string;
}> = [
  {
    regex: /^field required$/,
    translate: () => "es obligatorio",
  },
  {
    regex: /^ensure this value is greater than (\d+)$/,
    translate: (m) => `debe ser mayor a ${m[1]}`,
  },
  {
    regex: /^ensure this value is greater than or equal to (\d+)$/,
    translate: (m) => `debe ser mayor o igual a ${m[1]}`,
  },
  {
    regex: /^ensure this value is less than (\d+)$/,
    translate: (m) => `debe ser menor a ${m[1]}`,
  },
  {
    regex: /^ensure this value is less than or equal to (\d+)$/,
    translate: (m) => `debe ser menor o igual a ${m[1]}`,
  },
  {
    regex: /^value is not a valid integer$/,
    translate: () => "debe ser un numero entero",
  },
  {
    regex: /^value is not a valid float$/,
    translate: () => "debe ser un numero",
  },
  {
    regex: /^ensure this value has at least (\d+) characters$/,
    translate: (m) => `debe tener al menos ${m[1]} caracteres`,
  },
  {
    regex: /^ensure this value has at most (\d+) characters$/,
    translate: (m) => `debe tener como maximo ${m[1]} caracteres`,
  },
  {
    regex: /^string does not match regex/,
    translate: () => "tiene un formato invalido",
  },
  {
    regex: /^value is not a valid email address$/,
    translate: () => "debe ser un email valido",
  },
  {
    regex: /^unexpected value; permitted: (.+)$/,
    translate: (m) => `debe ser uno de: ${m[1]}`,
  },
];

/**
 * Extracts the field name from a Pydantic `loc` array.
 * Skips the leading "body" segment if present, then joins the rest.
 */
function extractFieldName(loc: string[]): string {
  const segments = loc[0] === "body" || loc[0] === "query" ? loc.slice(1) : loc;
  return segments[segments.length - 1] ?? "desconocido";
}

/**
 * Converts a snake_case field ID to Title Case with spaces.
 * Example: "nuevo_campo" → "Nuevo Campo"
 */
function fieldIdToLabel(fieldId: string): string {
  return fieldId
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

/**
 * Translates a Pydantic error message to a Spanish action phrase.
 * Returns the fallback "es invalido" if no pattern matches.
 */
function translatePydanticMessage(msg: string): string {
  for (const { regex, translate } of PYTHON_MESSAGE_PATTERNS) {
    const match = msg.match(regex);
    if (match) {
      return translate(match);
    }
  }
  return "es invalido";
}

// ── Public API ─────────────────────────────────────────────────────────

/**
 * Transforms an array of Pydantic 422 validation errors into
 * user-facing Spanish messages.
 *
 * @param errors - Array of error objects from `body.errors` in a 422 response.
 *   Each error has `loc` (path to the field), `msg` (Pydantic message), and `type`.
 * @returns Array of formatted messages like `["Precio Base debe ser mayor a 0"]`.
 *   Returns an empty array if errors is empty, null, or undefined.
 *
 * @example
 * formatValidationErrors([
 *   { loc: ["body", "precio_base"], msg: "ensure this value is greater than 0", type: "value_error" }
 * ])
 * // → ["Precio Base debe ser mayor a 0"]
 */
export function formatValidationErrors(errors: ErrorEntry[] | undefined | null): string[] {
  if (!errors || !Array.isArray(errors) || errors.length === 0) {
    return [];
  }

  return errors.map((e) => {
    const fieldName = extractFieldName(e.loc);
    const label = FIELD_LABELS[fieldName] ?? fieldIdToLabel(fieldName);
    const action = translatePydanticMessage(e.msg);
    return `${label} ${action}`;
  });
}
