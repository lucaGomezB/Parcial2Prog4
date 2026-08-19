/**
 * Dashboard — Admin statistics and analytics page.
 * Uses TanStack Query for all data fetching.
 */
import { useState } from "react";
import {
  BarChart,
  PieChart,
  LineChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  Cell,
  CartesianGrid,
  Bar,
  Pie,
  Line,
} from "recharts";
import {
  useResumen,
  useVentasPeriodo,
  useProductosTop,
  usePedidosEstado,
  useIngresosFormaPago,
} from "@/features/estadisticas/hooks/useEstadisticas";
import { formatCurrency } from "@/shared/utils/formatCurrency";

// ── Constants ──

const ESTADO_COLORS: Record<string, string> = {
  PENDIENTE: "#eab308",
  CONFIRMADO: "#3b82f6",
  EN_PREP: "#6366f1",
  ENTREGADO: "#22c55e",
  CANCELADO: "#ef4444",
};

const ESTADO_LABELS: Record<string, string> = {
  PENDIENTE: "Pendiente",
  CONFIRMADO: "Confirmado",
  EN_PREP: "En Preparacion",
  ENTREGADO: "Entregado",
  CANCELADO: "Cancelado",
};

const FALLBACK_ESTADO_COLOR = "#9ca3af";
const PRODUCT_NAME_MAX_LEN = 22;

function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 3) + "...";
}

function dateOffset(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().split("T")[0];
}

// ── Sub-components ──

function StatCard({ label, value, accentColor }: { label: string; value: string; accentColor: string; }) {
  return (
    <div className={`bg-white rounded-lg shadow border-l-4 ${accentColor} p-4`}>
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className="text-xl font-bold text-gray-800">{value}</p>
    </div>
  );
}

function ChartSection({ title, loading, empty, emptyMessage, error, onRetry, children }: {
  title: string; loading: boolean; empty: boolean; emptyMessage: string; error: string | null; onRetry: () => void; children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold text-gray-700 mb-3">{title}</h3>
      {loading && (
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
          <span className="ml-2 text-gray-500 text-sm">Cargando...</span>
        </div>
      )}
      {!loading && error && (
        <div className="text-center py-8">
          <p className="text-red-500 text-sm mb-2">{error}</p>
          <button onClick={onRetry} className="text-blue-600 text-sm underline cursor-pointer">Reintentar</button>
        </div>
      )}
      {!loading && !error && empty && (
        <div className="text-center py-8">
          <p className="text-gray-400 text-sm">{emptyMessage}</p>
        </div>
      )}
      {!loading && !error && !empty && children}
    </div>
  );
}

function PeriodSelector({ value, onChange }: { value: string; onChange: (ag: "day" | "week" | "month") => void; }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span className="text-sm text-gray-600">Agrupar por:</span>
      {(["day", "week", "month"] as const).map((ag) => (
        <button key={ag} onClick={() => onChange(ag)} className={`px-3 py-1 text-xs rounded border cursor-pointer transition-colors ${value === ag ? "bg-blue-600 text-white border-blue-600" : "bg-white text-gray-600 border-gray-300 hover:bg-gray-100"}`}>
          {ag === "day" ? "Dias" : ag === "week" ? "Semanas" : "Meses"}
        </button>
      ))}
    </div>
  );
}

// ── Main Page ──

export default function Dashboard() {
  const [agrupacion, setAgrupacion] = useState<"day" | "week" | "month">("day");

  const hoy = dateOffset(0);
  const rangeMap: Record<string, number> = { day: 30, week: 90, month: 365 };
  const desde = dateOffset(rangeMap[agrupacion]);

  // ── TanStack Query hooks ──
  const resumenQuery = useResumen();
  const ventasPeriodoQuery = useVentasPeriodo(desde, hoy, agrupacion);
  const productosTopQuery = useProductosTop(10);
  const pedidosEstadoQuery = usePedidosEstado();
  const ingresosFPQuery = useIngresosFormaPago(dateOffset(30), hoy);

  const allFailed = resumenQuery.isError && ventasPeriodoQuery.isError && productosTopQuery.isError && pedidosEstadoQuery.isError && ingresosFPQuery.isError;

  const handleAgrupacionChange = (newAg: "day" | "week" | "month") => {
    setAgrupacion(newAg);
  };

  if (allFailed) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">Dashboard de Estadisticas</h1>
        <div className="text-center py-12">
          <p className="text-red-600 text-lg mb-4">No se pudieron cargar los datos del dashboard. Verifique su conexion.</p>
          <button onClick={() => { resumenQuery.refetch(); ventasPeriodoQuery.refetch(); productosTopQuery.refetch(); pedidosEstadoQuery.refetch(); ingresosFPQuery.refetch(); }} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 cursor-pointer">Reintentar</button>
        </div>
      </div>
    );
  }

  const resumenData = resumenQuery.data;
  const ventasPeriodoData = ventasPeriodoQuery.data ?? [];
  const productosTopData = productosTopQuery.data ?? [];
  const pedidosEstadoData = pedidosEstadoQuery.data ?? [];
  const ingresosFPData = ingresosFPQuery.data ?? [];

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Dashboard de Estadisticas</h1>

      {/* ── Stat Cards Row ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {resumenQuery.isLoading ? (
          [1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white rounded-lg shadow border-l-4 border-l-gray-300 p-4 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-24 mb-2" />
              <div className="h-6 bg-gray-200 rounded w-32" />
            </div>
          ))
        ) : resumenQuery.isError ? (
          <div className="col-span-full">
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              <p className="text-sm">{(resumenQuery.error as Error)?.message || "Error"}</p>
              <button onClick={() => resumenQuery.refetch()} className="mt-1 text-xs text-red-600 underline cursor-pointer">Reintentar</button>
            </div>
          </div>
        ) : resumenData ? (
          <>
            <StatCard label="Ventas Hoy" value={formatCurrency(resumenData.ventas_hoy)} accentColor="border-l-blue-500" />
            <StatCard label="Ticket Promedio" value={formatCurrency(resumenData.ticket_promedio)} accentColor="border-l-green-500" />
            <StatCard label="Pedidos Activos" value={String(resumenData.pedidos_activos)} accentColor="border-l-orange-500" />
            <StatCard label="Mes Actual" value={formatCurrency(resumenData.mes_actual)} accentColor="border-l-purple-500" />
          </>
        ) : null}
      </div>

      {/* ── Charts Grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartSection title="Ventas por Periodo" loading={ventasPeriodoQuery.isLoading} empty={ventasPeriodoData.length === 0 && !ventasPeriodoQuery.isLoading && !ventasPeriodoQuery.isError} emptyMessage="Sin datos de ventas para este periodo" error={ventasPeriodoQuery.isError ? (ventasPeriodoQuery.error as Error)?.message || "Error" : null} onRetry={() => ventasPeriodoQuery.refetch()}>
          <PeriodSelector value={agrupacion} onChange={handleAgrupacionChange} />
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={ventasPeriodoData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="fecha" tick={{ fontSize: 11 }} tickFormatter={(val: string) => { const d = new Date(val + "T00:00:00"); return d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit" }); }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(val: number) => formatCurrency(val)} />
              <Tooltip formatter={(val: any) => { const n = typeof val === "number" ? val : Number(val); return [formatCurrency(n), "Total"]; }} labelFormatter={(label: React.ReactNode) => { const d = new Date(String(label ?? '') + "T00:00:00"); return d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" }); }} />
              <Line type="monotone" dataKey="total" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartSection>

        <ChartSection title="Top Productos" loading={productosTopQuery.isLoading} empty={productosTopData.length === 0 && !productosTopQuery.isLoading && !productosTopQuery.isError} emptyMessage="Sin datos de productos" error={productosTopQuery.isError ? (productosTopQuery.error as Error)?.message || "Error" : null} onRetry={() => productosTopQuery.refetch()}>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={productosTopData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(val: number) => formatCurrency(val)} />
              <YAxis dataKey="nombre" type="category" tick={{ fontSize: 10 }} tickFormatter={(val: string) => truncate(val, PRODUCT_NAME_MAX_LEN)} width={130} />
              <Tooltip formatter={(_val: any, _name: any, _props: any) => { return [formatCurrency(Number((_props as any)?.payload?.ingresos)), "Ingresos"]; }} labelFormatter={(label: React.ReactNode) => String(label ?? '')} />
              <Bar dataKey="ingresos" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartSection>

        <ChartSection title="Pedidos por Estado" loading={pedidosEstadoQuery.isLoading} empty={pedidosEstadoData.length === 0 && !pedidosEstadoQuery.isLoading && !pedidosEstadoQuery.isError} emptyMessage="Sin datos de pedidos" error={pedidosEstadoQuery.isError ? (pedidosEstadoQuery.error as Error)?.message || "Error" : null} onRetry={() => pedidosEstadoQuery.refetch()}>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={pedidosEstadoData} dataKey="cantidad" nameKey="estado_codigo" cx="50%" cy="50%" outerRadius={90} label={(entry: any) => `${ESTADO_LABELS[entry.estado_codigo] || entry.estado_codigo}: ${entry.cantidad}`}>
                {pedidosEstadoData.map((entry) => (<Cell key={entry.estado_codigo} fill={ESTADO_COLORS[entry.estado_codigo] || FALLBACK_ESTADO_COLOR} />))}
              </Pie>
              <Tooltip formatter={(_val: any, _name: any, entry: any) => { return [_val, ESTADO_LABELS[(entry as any)?.payload?.estado_codigo] || (entry as any)?.payload?.estado_codigo]; }} />
              <Legend formatter={(val: string) => ESTADO_LABELS[val] || val} />
            </PieChart>
          </ResponsiveContainer>
        </ChartSection>

        <ChartSection title="Ingresos por Forma de Pago" loading={ingresosFPQuery.isLoading} empty={ingresosFPData.length === 0 && !ingresosFPQuery.isLoading && !ingresosFPQuery.isError} emptyMessage="Sin datos de ingresos por forma de pago" error={ingresosFPQuery.isError ? (ingresosFPQuery.error as Error)?.message || "Error" : null} onRetry={() => ingresosFPQuery.refetch()}>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={ingresosFPData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(val: number) => formatCurrency(val)} />
              <YAxis dataKey="forma_pago_codigo" type="category" tick={{ fontSize: 11 }} width={100} />
              <Tooltip formatter={(_val: any) => { const n = typeof _val === "number" ? _val : Number(_val); return [formatCurrency(n), "Total"]; }} />
              <Bar dataKey="total" fill="#f59e0b" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartSection>
      </div>
    </div>
  );
}
