"""
Tests for shared-ingredient stock validation and the disponibilidad endpoint.

Covers:
- POST /pedidos/validar-stock reporting SHARED ingredient shortages (not just per-product).
- POST /pedidos/disponibilidad returning addable quantities that account for
  the current cart's consumption of shared ingredients.
"""
from decimal import Decimal


def _create_shared_ingredient_products(db_session):
    """Create two make-to-order products sharing a single ingredient.

    Returns (pizza, burger, ingredient) where both products use exactly
    1 unit of the shared ingredient (unidad_medida_id=5, porcion).
    """
    from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
    from app.modules.CatalogoDeProductos.Producto.models import Producto
    from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente

    ing = Ingrediente(
        nombre="Queso Compartido", descripcion="Test",
        precio_actual=Decimal("10.00"), stock_actual=3, unidad_medida_id=5,
    )
    db_session.add(ing)
    db_session.flush()

    def _producto(nombre):
        p = Producto(
            nombre=nombre, descripcion="Test",
            precio_base=Decimal("500.00"), precio_actual=Decimal("500.00"),
            tiempo_prep_min=5, disponible=True, es_producto_terminado=False,
        )
        db_session.add(p)
        db_session.flush()
        db_session.add(ProductoIngrediente(
            producto_id=p.id, ingrediente_id=ing.id,
            cantidad=Decimal("1.0"), es_removible=True, es_principal=True,
            orden=0, unidad_medida_id=5,
        ))
        db_session.flush()
        return p

    pizza = _producto("Pizza Compartida")
    burger = _producto("Burger Compartida")
    return pizza, burger, ing


class TestDisponibilidadSharedIngredient:
    def test_empty_cart_allows_full_stock(self, client, admin_headers, db_session):
        pizza, burger, _ = _create_shared_ingredient_products(db_session)

        resp = client.post("/api/v1/pedidos/disponibilidad", json={
            "carrito": [],
            "productos": [pizza.id, burger.id],
        }, headers=admin_headers)

        assert resp.status_code == 200
        data = resp.json()
        by_id = {p["producto_id"]: p["agregable"] for p in data["productos"]}
        # ingredient stock = 3, each product consumes 1 per unit -> 3 addable
        assert by_id[pizza.id] == 3
        assert by_id[burger.id] == 3

    def test_cart_consuming_shared_ingredient_reduces_availability(self, client, admin_headers, db_session):
        pizza, burger, _ = _create_shared_ingredient_products(db_session)

        # Cart already has 3 burgers -> consumes all 3 units of the shared ingredient.
        resp = client.post("/api/v1/pedidos/disponibilidad", json={
            "carrito": [{"producto_id": burger.id, "cantidad": 3}],
            "productos": [pizza.id],
        }, headers=admin_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["productos"][0]["agregable"] == 0

    def test_disponibilidad_reports_limitante_product(self, client, admin_headers, db_session):
        pizza, burger, _ = _create_shared_ingredient_products(db_session)

        # Cart has 3 burgers -> consumes all shared ingredient -> pizza's
        # limitante must name the burger (the product to reduce/remove).
        resp = client.post("/api/v1/pedidos/disponibilidad", json={
            "carrito": [{"producto_id": burger.id, "cantidad": 3}],
            "productos": [pizza.id],
        }, headers=admin_headers)

        assert resp.status_code == 200
        prod = resp.json()["productos"][0]
        assert prod["agregable"] == 0
        assert len(prod["limitantes"]) == 1
        assert prod["limitantes"][0]["producto_id"] == burger.id
        assert prod["limitantes"][0]["nombre"] == "Burger Compartida"

    def test_disponibilidad_no_limitantes_when_cart_does_not_share(self, client, admin_headers, db_session):
        pizza, burger, ing = _create_shared_ingredient_products(db_session)

        # Empty cart -> pizza has no limiting products (still fully addable).
        resp = client.post("/api/v1/pedidos/disponibilidad", json={
            "carrito": [],
            "productos": [pizza.id],
        }, headers=admin_headers)

        assert resp.status_code == 200
        prod = resp.json()["productos"][0]
        assert prod["agregable"] == 3
        assert prod["limitantes"] == []

    def test_added_product_becomes_unaddable_when_it_exhausts_shared_ingredient(self, client, admin_headers, db_session):
        """The recently-added product itself reports agregable=0 when its add
        consumed the last unit of a shared ingredient (Option B, forward-looking)."""
        pizza, _, ing = _create_shared_ingredient_products(db_session)
        ing.stock_actual = 1
        db_session.flush()

        # Cart already holds 1 pizza -> the single shared ingredient unit is
        # consumed -> pizza cannot be added again.
        resp = client.post("/api/v1/pedidos/disponibilidad", json={
            "carrito": [{"producto_id": pizza.id, "cantidad": 1}],
            "productos": [pizza.id],
        }, headers=admin_headers)

        assert resp.status_code == 200
        prod = resp.json()["productos"][0]
        assert prod["agregable"] == 0

    def test_terminado_product_uses_stock_manual(self, client, admin_headers, db_session):
        from app.modules.CatalogoDeProductos.Producto.models import Producto

        p = Producto(
            nombre="Gaseosa Terminada", descripcion="Test",
            precio_base=Decimal("500.00"), precio_actual=Decimal("500.00"),
            stock_manual=2, tiempo_prep_min=0, disponible=True,
            es_producto_terminado=True,
        )
        db_session.add(p)
        db_session.flush()

        # cart already has 1 -> only 1 more addable
        resp = client.post("/api/v1/pedidos/disponibilidad", json={
            "carrito": [{"producto_id": p.id, "cantidad": 1}],
            "productos": [p.id],
        }, headers=admin_headers)

        assert resp.status_code == 200
        assert resp.json()["productos"][0]["agregable"] == 1


class TestValidarStockSharedIngredient:
    def test_shared_ingredient_shortage_is_reported(self, client, admin_headers, db_session):
        pizza, burger, ing = _create_shared_ingredient_products(db_session)

        # 2 pizza + 2 burger = 4 units of the shared ingredient > stock 3.
        resp = client.post("/api/v1/pedidos/validar-stock", json={
            "detalles": [
                {"producto_id": pizza.id, "cantidad": 2},
                {"producto_id": burger.id, "cantidad": 2},
            ],
        }, headers=admin_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["valido"] is False
        # per-product derived stock is individually sufficient (3 >= 2), so no
        # product-level shortfall — the shortage is at the SHARED ingredient level.
        assert data["detalles"] == []
        assert len(data["ingredientes"]) == 1
        short = data["ingredientes"][0]
        assert short["ingrediente_id"] == ing.id
        assert short["cantidad_solicitada"] == 4
        assert short["stock_disponible"] == 3

    def test_no_shared_shortage_when_within_stock(self, client, admin_headers, db_session):
        pizza, burger, _ = _create_shared_ingredient_products(db_session)

        # 1 pizza + 1 burger = 2 units of shared ingredient <= stock 3.
        resp = client.post("/api/v1/pedidos/validar-stock", json={
            "detalles": [
                {"producto_id": pizza.id, "cantidad": 1},
                {"producto_id": burger.id, "cantidad": 1},
            ],
        }, headers=admin_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["valido"] is True
        assert data["ingredientes"] == []

    def test_shared_shortage_includes_unit_symbol(self, client, admin_headers, db_session):
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
        from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
        from app.modules.CatalogoDeProductos.Producto.models import Producto
        from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente

        um = UnidadMedida(nombre="Porcion", simbolo="porc", tipo="unidad", factor_conversion=Decimal("1"))
        db_session.add(um)
        db_session.flush()

        ing = Ingrediente(
            nombre="Queso Con Unidad", descripcion="Test",
            precio_actual=Decimal("10.00"), stock_actual=3, unidad_medida_id=um.id,
        )
        db_session.add(ing)
        db_session.flush()

        def _prod(nombre):
            p = Producto(
                nombre=nombre, descripcion="Test",
                precio_base=Decimal("100.00"), precio_actual=Decimal("100.00"),
                tiempo_prep_min=5, disponible=True, es_producto_terminado=False,
            )
            db_session.add(p)
            db_session.flush()
            db_session.add(ProductoIngrediente(
                producto_id=p.id, ingrediente_id=ing.id,
                cantidad=Decimal("1.0"), es_removible=True, es_principal=True,
                orden=0, unidad_medida_id=um.id,
            ))
            db_session.flush()
            return p

        a = _prod("Prod A Con Unidad")
        b = _prod("Prod B Con Unidad")

        resp = client.post("/api/v1/pedidos/validar-stock", json={
            "detalles": [
                {"producto_id": a.id, "cantidad": 2},
                {"producto_id": b.id, "cantidad": 2},
            ],
        }, headers=admin_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["valido"] is False
        short = data["ingredientes"][0]
        assert short["ingrediente_id"] == ing.id
        assert short["unidad_medida_simbolo"] == "porc"
