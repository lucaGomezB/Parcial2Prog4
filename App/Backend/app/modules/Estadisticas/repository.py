"""
Estadisticas repository — raw SQL aggregation queries.

All queries use session.exec(text(...)) with parameter binding.
PostgreSQL-specific DATE_TRUNC is safe here (no cross-DB requirement).

Per AD-1: raw SQL is chosen over SQLModel ORM for complex aggregations.
Per AD-3: this repository does NOT extend BaseRepository — it operates
across multiple tables and returns dicts, not SQLModel entities.
"""
from decimal import Decimal
from datetime import date
from sqlmodel import Session, text


class EstadisticasRepository:
    """Read-only repository for analytics aggregation queries."""

    def __init__(self, session: Session):
        self.session = session

    # ── Ventas por Periodo ────────────────────────────────────────────────

    def get_ventas_periodo(
        self, desde: date, hasta: date, agrupacion: str
    ) -> list[dict]:
        """Aggregate order totals grouped by time interval.

        Returns list of dicts with keys: fecha (str), total (Decimal).
        Excludes CANCELADO orders and soft-deleted records.
        """
        result = self.session.exec(
            text(
                f"""
                SELECT
                    DATE_TRUNC('{agrupacion}', created_at)::date::text AS fecha,
                    COALESCE(SUM(total), 0) AS total
                FROM pedido
                WHERE estado_codigo != 'CANCELADO'
                  AND deleted_at IS NULL
                  AND DATE(created_at) BETWEEN :desde AND :hasta
                GROUP BY DATE_TRUNC('{agrupacion}', created_at)
                ORDER BY DATE_TRUNC('{agrupacion}', created_at)
                """
            ).params(desde=desde, hasta=hasta)
        )
        return [{"fecha": row.fecha, "total": row.total} for row in result]

    # ── Top Productos ─────────────────────────────────────────────────────

    def get_productos_top(self, limit: int) -> list[dict]:
        """Top products by total revenue (SUM of subtotal_snap).

        Returns list of dicts with keys: producto_id, nombre,
        cantidad_vendida, ingresos. Excludes CANCELADO orders and
        soft-deleted records. Revenue uses subtotal_snap (NOT precio_snapshot).
        """
        result = self.session.exec(
            text(
                """
                SELECT
                    dp.producto_id,
                    dp.nombre_snapshot AS nombre,
                    SUM(dp.cantidad) AS cantidad_vendida,
                    SUM(dp.subtotal_snap) AS ingresos
                FROM detallepedido dp
                JOIN pedido p ON dp.pedido_id = p.id
                WHERE p.estado_codigo != 'CANCELADO'
                  AND p.deleted_at IS NULL
                GROUP BY dp.producto_id, dp.nombre_snapshot
                ORDER BY ingresos DESC
                LIMIT :limit
                """
            ).params(limit=limit)
        )
        return [
            {
                "producto_id": row.producto_id,
                "nombre": row.nombre,
                "cantidad_vendida": row.cantidad_vendida,
                "ingresos": row.ingresos,
            }
            for row in result
        ]

    # ── Pedidos por Estado ─────────────────────────────────────────────────

    def get_pedidos_por_estado(self) -> list[dict]:
        """Count non-deleted orders grouped by estado_codigo.

        Returns list of dicts with keys: estado_codigo, cantidad.
        ORDER BY cantidad DESC for chart relevance.
        """
        result = self.session.exec(
            text(
                """
                SELECT estado_codigo, COUNT(*) AS cantidad
                FROM pedido
                WHERE deleted_at IS NULL
                GROUP BY estado_codigo
                ORDER BY cantidad DESC
                """
            )
        )
        return [
            {"estado_codigo": row.estado_codigo, "cantidad": row.cantidad}
            for row in result
        ]

    # ── Resumen KPIs ──────────────────────────────────────────────────────

    def get_resumen_kpis(self) -> dict:
        """Four scalar KPI queries executed in a single method.

        (a) ventas_hoy: SUM(total) for today, non-cancelled, non-deleted
        (b) ticket_promedio: AVG(total) same filters
        (c) pedidos_activos: COUNT(*) in non-terminal states, non-deleted
        (d) mes_actual: SUM(total) for current month, non-cancelled, non-deleted

        Returns dict with all four values. COALESCE ensures 0 instead of NULL.
        """
        # (a) ventas_hoy
        result_a = self.session.exec(
            text(
                """
                SELECT COALESCE(SUM(total), 0) AS ventas_hoy
                FROM pedido
                WHERE DATE(created_at) = CURRENT_DATE
                  AND estado_codigo != 'CANCELADO'
                  AND deleted_at IS NULL
                """
            )
        )
        ventas_hoy = result_a.scalar()

        # (b) ticket_promedio
        result_b = self.session.exec(
            text(
                """
                SELECT COALESCE(AVG(total), 0) AS ticket_promedio
                FROM pedido
                WHERE DATE(created_at) = CURRENT_DATE
                  AND estado_codigo != 'CANCELADO'
                  AND deleted_at IS NULL
                """
            )
        )
        ticket_promedio = result_b.scalar()

        # (c) pedidos_activos — non-terminal states only
        result_c = self.session.exec(
            text(
                """
                SELECT COUNT(*) AS pedidos_activos
                FROM pedido
                WHERE estado_codigo IN ('PENDIENTE', 'CONFIRMADO', 'EN_PREP')
                  AND deleted_at IS NULL
                """
            )
        )
        pedidos_activos = result_c.scalar()

        # (d) mes_actual
        result_d = self.session.exec(
            text(
                """
                SELECT COALESCE(SUM(total), 0) AS mes_actual
                FROM pedido
                WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
                  AND estado_codigo != 'CANCELADO'
                  AND deleted_at IS NULL
                """
            )
        )
        mes_actual = result_d.scalar()

        return {
            "ventas_hoy": ventas_hoy,
            "ticket_promedio": ticket_promedio,
            "pedidos_activos": pedidos_activos,
            "mes_actual": mes_actual,
        }

    # ── Ingresos por Forma de Pago ─────────────────────────────────────────

    def get_ingresos_por_forma_pago(
        self, desde: date, hasta: date
    ) -> list[dict]:
        """Revenue grouped by payment method.

        Returns list of dicts with keys: forma_pago_codigo, total.
        Counts all confirmed orders regardless of payment method.
        MERCADOPAGO pedidos are created in CONFIRMADO state only after
        payment approval, so the estado filter is sufficient.
        Excludes PENDIENTE, CANCELADO, and soft-deleted records.
        """
        result = self.session.exec(
            text(
                """
                SELECT
                    p.forma_pago_codigo,
                    COALESCE(SUM(p.total), 0) AS total
                FROM pedido p
                WHERE p.estado_codigo IN ('CONFIRMADO', 'EN_PREP', 'ENTREGADO')
                  AND p.deleted_at IS NULL
                  AND DATE(p.created_at) BETWEEN :desde AND :hasta
                GROUP BY p.forma_pago_codigo
                ORDER BY total DESC
                """
            ).params(desde=desde, hasta=hasta)
        )
        return [
            {"forma_pago_codigo": row.forma_pago_codigo, "total": row.total}
            for row in result
        ]
