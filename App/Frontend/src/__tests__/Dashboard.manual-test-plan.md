# Dashboard Manual Test Plan

> **NOTE**: This project does not have a test runner configured (no vitest/jest).
> These are manual verification steps that should be performed before merging.
> When a test runner is added, these scenarios should be converted to automated tests.

## Prerequisites

- Backend running with seed data or test data in the database
- Logged in as an ADMIN user
- Navigate to `/admin/dashboard`

---

## 11.1: Stat Cards Render

**Purpose**: Verify all 4 KPI cards display with correct labels and formatted values.

**Steps**:
1. Log in as ADMIN.
2. Navigate to `/admin/dashboard`.
3. Wait for the dashboard to load (spinner disappears).

**Expected**:
- Four cards are visible in a responsive grid (4 columns on wide screen, 2 on tablet, 1 on mobile).
- Card 1: "Ventas Hoy" with a currency-formatted ARS value (e.g., "$ 1.500,00").
- Card 2: "Ticket Promedio" with a currency-formatted ARS value.
- Card 3: "Pedidos Activos" with an integer value.
- Card 4: "Mes Actual" with a currency-formatted ARS value.
- Each card has a colored left border (blue, green, orange, purple).
- Cards have white background, rounded corners, and shadow.

---

## 11.2: Charts Render

**Purpose**: Verify all 4 chart sections display.

**Steps**:
1. Log in as ADMIN.
2. Navigate to `/admin/dashboard`.
3. Wait for all data to load.

**Expected**:
- "Ventas por Periodo": LineChart visible with period selector buttons (Dia/Semana/Mes).
- "Top Productos": vertical BarChart with product names on Y-axis.
- "Pedidos por Estado": PieChart with color-coded slices and legend.
- "Ingresos por Forma de Pago": horizontal BarChart with payment methods.
- Each chart renders within a white card with shadow.
- Charts are responsive (resize correctly when window width changes).

---

## 11.3: Loading State

**Purpose**: Verify spinner/skeleton displays while data is being fetched.

**Steps**:
1. Open browser DevTools Network tab.
2. Throttle network to Slow 3G (or use airplane mode then disable to create a gap).
3. Log in as ADMIN and navigate to `/admin/dashboard`.

**Expected**:
- Stat cards show animated pulse skeleton placeholders (gray rectangles).
- Each chart section shows a centered spinner with "Cargando..." text.
- No error messages appear while loading.
- Content transitions from skeleton/spinner to real data when fetch completes.

---

## 11.4: Error State

**Purpose**: Verify error messages and retry buttons appear on API failure.

**Steps**:
1. Stop the backend server (or modify config to point to invalid URL).
2. Log in as ADMIN and navigate to `/admin/dashboard`.
3. Observe the page after API calls fail.

**Expected**:
- If ALL 5 endpoints fail, a centered error message appears:
  "No se pudieron cargar los datos del dashboard. Verifique su conexion."
  with a "Reintentar" button.
- If only some endpoints fail, individual chart sections show their own
  error message with "Reintentar" button specific to that chart.
- Clicking "Reintentar" re-attempts the failed requests.
- After restarting the backend and clicking retry, data loads normally.

---

## 11.5: Empty State

**Purpose**: Verify "Sin datos" messages appear when API returns empty arrays.

**Steps**:
1. Ensure the database has NO orders (or use a fresh empty database).
2. Log in as ADMIN and navigate to `/admin/dashboard`.

**Expected**:
- Each chart section shows its specific empty message:
  - Ventas por Periodo: "Sin datos de ventas para este periodo"
  - Top Productos: "Sin datos de productos"
  - Pedidos por Estado: "Sin datos de pedidos"
  - Ingresos por Forma de Pago: "Sin datos de ingresos por forma de pago"
- Stat cards show "$ 0,00" for monetary values and "0" for Pedidos Activos.
- No errors appear.
- No loading spinners remain visible.

---

## 11.6: PeriodSelector Interaction

**Purpose**: Verify period selector buttons change agrupacion and trigger re-fetch.

**Steps**:
1. Log in as ADMIN and navigate to `/admin/dashboard`.
2. Wait for initial data load.
3. Click "Semana" button in the Ventas por Periodo section.
4. Click "Mes" button.
5. Click "Dia" button to return.

**Expected**:
- Clicking a different period button:
  - The active button turns blue with white text.
  - The previously active button returns to gray.
  - The Ventas por Periodo chart shows a loading spinner briefly.
  - New data loads with the selected aggregation.
  - ONLY the Ventas por Periodo chart re-fetches (other charts remain unchanged).
- The X-axis labels change to reflect the selected grouping:
  - Dia: day-level dates (e.g., "10/06", "11/06")
  - Semana: week-level dates
  - Mes: month-level dates
- The URL includes correct query params (agrupacion=week, agrupacion=month).

---

## 11.7: ADMIN Auth Guard

**Purpose**: Verify non-ADMIN users cannot access the dashboard.

**Steps**:
1. Log in as a CLIENT user (non-ADMIN role).
2. Manually navigate to `/admin/dashboard` in the URL bar.
3. Log in as a STOCK user and repeat step 2.
4. Log in as a PEDIDOS user and repeat step 2.

**Expected**:
- CLIENT user: redirected to `/productos` (the catch-all `*` route).
  Dashboard page does NOT render.
- STOCK user: redirected to `/productos`.
- PEDIDOS user: redirected to `/pedidos`.
- Only ADMIN users can access `/admin/dashboard` and see the full dashboard.
- Unauthenticated users are redirected to `/login`.
- The backend also returns 403 for non-ADMIN API calls (defense in depth).

---

## 11.8: API Client Types

**Purpose**: Verify TypeScript interfaces and API client functions compile without errors.

**Steps**:
1. Run `npx tsc --noEmit` in the `Frontend/` directory.

**Expected**:
- No TypeScript errors in `Frontend/src/api/estadisticas.ts`.
- All interfaces are properly exported and used.
- Monetary fields (`ventas_hoy`, `ticket_promedio`, `mes_actual`, `total`, `ingresos`)
  are typed as `string`.
- The Dashboard component imports and uses the correct types.
- `apiFetch` generic type parameter matches the endpoint response type.
