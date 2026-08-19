"""
Tests for UnidadMedida — measurement unit catalog entity.

Covers model creation, constraints, repository queries, and API endpoints.
Uses real SQLite DB via conftest fixtures.
"""
import pytest
from decimal import Decimal
from fastapi import status
from datetime import datetime
from sqlmodel import Session, select

# ═══════════════════════════════════════════════════════════════════════════
# Model tests
# ═══════════════════════════════════════════════════════════════════════════

class TestUnidadMedidaModel:

    def test_create_unidad_medida_sets_created_at(self, db_session):
        """CREATED a UnidadMedida sets created_at to a UTC datetime."""
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida

        unit = UnidadMedida(nombre="kilogramo", simbolo="kg", tipo="masa")
        db_session.add(unit)
        db_session.flush()

        assert unit.id is not None
        assert unit.created_at is not None
        assert isinstance(unit.created_at, datetime)

    def test_unique_nombre_constraint(self, db_session):
        """Duplicate nombre raises IntegrityError."""
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
        from sqlalchemy.exc import IntegrityError

        db_session.add(UnidadMedida(nombre="kilogramo", simbolo="kg", tipo="masa"))
        db_session.flush()

        with pytest.raises(IntegrityError):
            db_session.add(UnidadMedida(nombre="kilogramo", simbolo="kg2", tipo="masa"))
            db_session.flush()

    def test_unique_simbolo_constraint(self, db_session):
        """Duplicate simbolo raises IntegrityError."""
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
        from sqlalchemy.exc import IntegrityError

        db_session.add(UnidadMedida(nombre="kilogramo", simbolo="kg", tipo="masa"))
        db_session.flush()

        with pytest.raises(IntegrityError):
            db_session.add(UnidadMedida(nombre="kilogramo2", simbolo="kg", tipo="masa"))
            db_session.flush()

    def test_no_updated_at_column(self, db_session):
        """UnidadMedida does NOT have updated_at or deleted_at columns."""
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida

        unit = UnidadMedida(nombre="litro", simbolo="L", tipo="volumen")
        db_session.add(unit)
        db_session.flush()

        # Verify the object has no updated_at or deleted_at attribute
        assert not hasattr(unit, 'updated_at')
        assert not hasattr(unit, 'deleted_at')

    def test_surrogate_id_is_bigint(self, db_session):
        """UnidadMedida uses a BIGSERIAL surrogate PK (integer type)."""
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida

        unit = UnidadMedida(nombre="gramo", simbolo="g", tipo="masa")
        db_session.add(unit)
        db_session.flush()

        assert isinstance(unit.id, int)
        assert unit.id >= 1


# ═══════════════════════════════════════════════════════════════════════════
# Repository tests
# ═══════════════════════════════════════════════════════════════════════════

class TestUnidadMedidaRepository:

    def _seed_units(self, db_session):
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida

        units = [
            UnidadMedida(nombre="kilogramo", simbolo="kg", tipo="masa"),
            UnidadMedida(nombre="gramo", simbolo="g", tipo="masa"),
            UnidadMedida(nombre="litro", simbolo="L", tipo="volumen"),
            UnidadMedida(nombre="porcion", simbolo="p", tipo="unidad"),
        ]
        for u in units:
            db_session.add(u)
        db_session.flush()

    def test_get_all_ordered_by_tipo_then_nombre(self, db_session):
        """get_all() returns units ordered by tipo then nombre."""
        self._seed_units(db_session)
        from app.modules.CatalogoDeProductos.UnidadMedida.repository import UnidadMedidaRepository

        repo = UnidadMedidaRepository(db_session)
        result = repo.get_all()

        assert len(result) == 4
        # Expected order: masa (gramo, kilogramo), unidad (porcion), volumen (litro)
        # Within masa: gramo before kilogramo alphabetically
        assert result[0].nombre == "gramo"
        assert result[1].nombre == "kilogramo"
        assert result[2].nombre == "porcion"
        assert result[3].nombre == "litro"

    def test_get_all_filtered_by_tipo(self, db_session):
        """get_all(tipo_filter='masa') returns only masa units."""
        self._seed_units(db_session)
        from app.modules.CatalogoDeProductos.UnidadMedida.repository import UnidadMedidaRepository

        repo = UnidadMedidaRepository(db_session)
        result = repo.get_all(tipo_filter="masa")

        assert len(result) == 2
        assert all(u.tipo == "masa" for u in result)

    def test_get_by_id_returns_correct_unit(self, db_session):
        """get_by_id returns the correct unit."""
        self._seed_units(db_session)
        from app.modules.CatalogoDeProductos.UnidadMedida.repository import UnidadMedidaRepository

        repo = UnidadMedidaRepository(db_session)
        kg = db_session.exec(
            select(
                __import__('app.modules.CatalogoDeProductos.UnidadMedida.models', fromlist=['UnidadMedida']).UnidadMedida
            ).where(
                __import__('app.modules.CatalogoDeProductos.UnidadMedida.models', fromlist=['UnidadMedida']).UnidadMedida.nombre == "kilogramo"
            )
        ).first()

        result = repo.get_by_id(kg.id)
        assert result is not None
        assert result.nombre == "kilogramo"
        assert result.simbolo == "kg"

    def test_get_by_id_nonexistent_returns_none(self, db_session):
        """get_by_id with nonexistent id returns None."""
        from app.modules.CatalogoDeProductos.UnidadMedida.repository import UnidadMedidaRepository

        repo = UnidadMedidaRepository(db_session)
        result = repo.get_by_id(99999)
        assert result is None

    def test_has_references_returns_false_when_none(self, db_session):
        """has_references returns False when no FK references exist."""
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
        from app.modules.CatalogoDeProductos.UnidadMedida.repository import UnidadMedidaRepository

        unit = UnidadMedida(nombre="docena", simbolo="doc", tipo="unidad")
        db_session.add(unit)
        db_session.flush()

        repo = UnidadMedidaRepository(db_session)
        assert repo.has_references(unit.id) is False

    def test_has_references_returns_true_when_producto_references(self, db_session):
        """has_references returns True when a Producto references the unit."""
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
        from app.modules.CatalogoDeProductos.Producto.models import Producto
        from app.modules.CatalogoDeProductos.UnidadMedida.repository import UnidadMedidaRepository

        unit = UnidadMedida(nombre="mililitro", simbolo="mL", tipo="volumen")
        db_session.add(unit)
        db_session.flush()

        prod = Producto(
            nombre="Test Product",
            precio_base=100,
            precio_actual=100,
            stock_cantidad=10,
            unidad_medida_id=unit.id,
        )
        db_session.add(prod)
        db_session.flush()

        repo = UnidadMedidaRepository(db_session)
        assert repo.has_references(unit.id) is True


# ═══════════════════════════════════════════════════════════════════════════
# Service tests
# ═══════════════════════════════════════════════════════════════════════════

class TestUnidadMedidaService:

    def _seed_roles(self, db_session):
        from app.modules.IdentidadYAcceso.Rol.models import Rol
        for codigo, nombre, desc in [
            ("ADMIN", "Admin", ""),
            ("STOCK", "Stock", ""),
            ("PEDIDOS", "Pedidos", ""),
            ("CLIENT", "Cliente", ""),
        ]:
            if not db_session.exec(select(Rol).where(Rol.codigo == codigo)).first():
                db_session.add(Rol(codigo=codigo, nombre=nombre, descripcion=desc))
        db_session.flush()

    def _seed_kg_unit(self, db_session):
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
        existing = db_session.exec(
            select(UnidadMedida).where(UnidadMedida.nombre == "kilogramo")
        ).first()
        if not existing:
            unit = UnidadMedida(nombre="kilogramo", simbolo="kg", tipo="masa")
            db_session.add(unit)
            db_session.flush()
            return unit
        return existing

    def test_get_all_returns_all_units(self, db_session):
        """Service get_all returns all units."""
        self._seed_kg_unit(db_session)
        from app.modules.CatalogoDeProductos.UnidadMedida.service import UnidadMedidaService

        result = UnidadMedidaService.get_all(db_session)
        assert len(result) >= 1
        assert isinstance(result, list)

    def test_get_all_with_tipo_filter(self, db_session):
        """Service get_all with tipo_filter returns filtered results."""
        self._seed_kg_unit(db_session)
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
        from app.modules.CatalogoDeProductos.UnidadMedida.service import UnidadMedidaService

        # Add a volume unit
        db_session.add(UnidadMedida(nombre="litro", simbolo="L", tipo="volumen"))
        db_session.flush()

        result = UnidadMedidaService.get_all(db_session, tipo_filter="masa")
        assert len(result) >= 1
        assert all(u.tipo == "masa" for u in result)

    def test_get_by_id_returns_unit(self, db_session):
        """Service get_by_id returns the correct unit."""
        unit = self._seed_kg_unit(db_session)
        from app.modules.CatalogoDeProductos.UnidadMedida.service import UnidadMedidaService

        result = UnidadMedidaService.get_by_id(db_session, unit.id)
        assert result is not None
        assert result.nombre == "kilogramo"

    def test_get_by_id_nonexistent_returns_none(self, db_session):
        """Service get_by_id with bad id returns None."""
        from app.modules.CatalogoDeProductos.UnidadMedida.service import UnidadMedidaService

        result = UnidadMedidaService.get_by_id(db_session, 99999)
        assert result is None

    def test_create_returns_unit_with_id(self, db_session):
        """Service create creates a unit and returns it with an id."""
        from app.modules.CatalogoDeProductos.UnidadMedida.schemas import UnidadMedidaCreate
        from app.modules.CatalogoDeProductos.UnidadMedida.service import UnidadMedidaService

        data = UnidadMedidaCreate(nombre="gramo", simbolo="g", tipo="masa")
        result = UnidadMedidaService.create(db_session, data)

        assert result.id is not None
        assert result.nombre == "gramo"
        assert result.simbolo == "g"
        assert result.tipo == "masa"

    def test_update_changes_fields(self, db_session):
        """Service update changes specified fields."""
        unit = self._seed_kg_unit(db_session)
        from app.modules.CatalogoDeProductos.UnidadMedida.schemas import UnidadMedidaUpdate
        from app.modules.CatalogoDeProductos.UnidadMedida.service import UnidadMedidaService

        data = UnidadMedidaUpdate(simbolo="KG")
        result = UnidadMedidaService.update(db_session, unit.id, data)

        assert result is not None
        assert result.simbolo == "KG"
        assert result.nombre == "kilogramo"  # unchanged

    def test_update_nonexistent_returns_none(self, db_session):
        """Service update on nonexistent id returns None."""
        from app.modules.CatalogoDeProductos.UnidadMedida.schemas import UnidadMedidaUpdate
        from app.modules.CatalogoDeProductos.UnidadMedida.service import UnidadMedidaService

        data = UnidadMedidaUpdate(simbolo="KG")
        result = UnidadMedidaService.update(db_session, 99999, data)
        assert result is None

    def test_delete_removes_unit(self, db_session):
        """Service delete removes the unit."""
        unit = self._seed_kg_unit(db_session)
        from app.modules.CatalogoDeProductos.UnidadMedida.service import UnidadMedidaService

        result = UnidadMedidaService.delete(db_session, unit.id)
        assert result is True

        # Verify it's gone
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
        exists = db_session.exec(
            select(UnidadMedida).where(UnidadMedida.id == unit.id)
        ).first()
        assert exists is None

    def test_delete_referenced_unit_raises_value_error(self, db_session):
        """Service delete raises ValueError when unit has FK references."""
        unit = self._seed_kg_unit(db_session)
        from app.modules.CatalogoDeProductos.Producto.models import Producto
        from app.modules.CatalogoDeProductos.UnidadMedida.service import UnidadMedidaService

        # Create a product referencing this unit
        prod = Producto(
            nombre="Test Prod",
            precio_base=100,
            precio_actual=100,
            stock_cantidad=10,
            unidad_medida_id=unit.id,
        )
        db_session.add(prod)
        db_session.flush()

        with pytest.raises(ValueError) as exc_info:
            UnidadMedidaService.delete(db_session, unit.id)
        assert "en uso" in str(exc_info.value).lower() or "referencia" in str(exc_info.value).lower()

    def test_delete_nonexistent_returns_false(self, db_session):
        """Service delete on nonexistent id returns False."""
        from app.modules.CatalogoDeProductos.UnidadMedida.service import UnidadMedidaService

        result = UnidadMedidaService.delete(db_session, 99999)
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════
# API endpoint tests
# ═══════════════════════════════════════════════════════════════════════════

class TestUnidadMedidaAPI:

    def _seed_roles(self, db_session):
        from app.modules.IdentidadYAcceso.Rol.models import Rol
        for codigo, nombre, desc in [
            ("ADMIN", "Admin", ""),
            ("STOCK", "Stock", ""),
            ("PEDIDOS", "Pedidos", ""),
            ("CLIENT", "Cliente", ""),
        ]:
            if not db_session.exec(select(Rol).where(Rol.codigo == codigo)).first():
                db_session.add(Rol(codigo=codigo, nombre=nombre, descripcion=desc))
        db_session.flush()

    def _seed_unit(self, db_session, nombre="kilogramo", simbolo="kg", tipo="masa"):
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
        existing = db_session.exec(
            select(UnidadMedida).where(UnidadMedida.nombre == nombre)
        ).first()
        if not existing:
            unit = UnidadMedida(nombre=nombre, simbolo=simbolo, tipo=tipo)
            db_session.add(unit)
            db_session.flush()
            return unit
        return existing

    def test_list_unidades_medida_returns_array(self, client, admin_headers, db_session):
        """GET /api/v1/unidades-medida/ returns an array."""
        self._seed_roles(db_session)
        self._seed_unit(db_session)

        response = client.get("/api/v1/unidades-medida/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_unidades_medida_with_tipo_filter(self, client, admin_headers, db_session):
        """GET /api/v1/unidades-medida/?tipo=masa returns only masa units."""
        self._seed_roles(db_session)
        self._seed_unit(db_session, "kilogramo", "kg", "masa")
        self._seed_unit(db_session, "litro", "L", "volumen")

        response = client.get("/api/v1/unidades-medida/?tipo=masa", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert all(u.get("tipo") == "masa" for u in data)

    def test_get_unidad_medida_by_id(self, client, admin_headers, db_session):
        """GET /api/v1/unidades-medida/{id} returns the unit."""
        self._seed_roles(db_session)
        unit = self._seed_unit(db_session)
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida

        found = db_session.exec(
            select(UnidadMedida).where(UnidadMedida.nombre == "kilogramo")
        ).first()

        response = client.get(f"/api/v1/unidades-medida/{found.id}", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["nombre"] == "kilogramo"

    def test_get_unidad_medida_not_found_returns_404(self, client, admin_headers, db_session):
        """GET nonexistent unidad-medida returns 404."""
        self._seed_roles(db_session)
        response = client.get("/api/v1/unidades-medida/99999", headers=admin_headers)
        assert response.status_code == 404

    def test_create_unidad_medida_as_admin(self, client, admin_headers, db_session):
        """POST as ADMIN creates a unit and returns 201."""
        self._seed_roles(db_session)

        response = client.post(
            "/api/v1/unidades-medida/",
            json={"nombre": "miligramo", "simbolo": "mg", "tipo": "masa"},
            headers=admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "miligramo"
        assert data["id"] is not None

    def test_create_unidad_medida_with_invalid_tipo_returns_422(self, client, admin_headers, db_session):
        """POST with invalid tipo returns 422."""
        self._seed_roles(db_session)

        response = client.post(
            "/api/v1/unidades-medida/",
            json={"nombre": "metro", "simbolo": "m", "tipo": "longitud"},
            headers=admin_headers,
        )
        assert response.status_code == 422

    def test_update_unidad_medida_as_admin(self, client, admin_headers, db_session):
        """PUT as ADMIN updates a unit."""
        self._seed_roles(db_session)
        unit = self._seed_unit(db_session)
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
        found = db_session.exec(
            select(UnidadMedida).where(UnidadMedida.nombre == "kilogramo")
        ).first()

        response = client.put(
            f"/api/v1/unidades-medida/{found.id}",
            json={"simbolo": "KG"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["simbolo"] == "KG"

    def test_delete_unidad_medida_as_admin(self, client, admin_headers, db_session):
        """DELETE as ADMIN removes an unreferenced unit."""
        self._seed_roles(db_session)
        unit = self._seed_unit(db_session, "porcion", "p", "unidad")
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
        found = db_session.exec(
            select(UnidadMedida).where(UnidadMedida.nombre == "porcion")
        ).first()

        response = client.delete(
            f"/api/v1/unidades-medida/{found.id}",
            headers=admin_headers,
        )
        assert response.status_code == 204

    def test_delete_referenced_unit_fails(self, client, admin_headers, db_session):
        """DELETE a referenced unit returns 400."""
        self._seed_roles(db_session)
        unit = self._seed_unit(db_session)
        from app.modules.CatalogoDeProductos.Producto.models import Producto
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
        found = db_session.exec(
            select(UnidadMedida).where(UnidadMedida.nombre == "kilogramo")
        ).first()

        # Create a product referencing this unit
        prod = Producto(
            nombre="Ref Product",
            precio_base=100,
            precio_actual=100,
            stock_cantidad=10,
            unidad_medida_id=found.id,
        )
        db_session.add(prod)
        db_session.flush()

        response = client.delete(
            f"/api/v1/unidades-medida/{found.id}",
            headers=admin_headers,
        )
        assert response.status_code == 400
        error_detail = response.json().get("detail", "")
        assert "uso" in error_detail.lower() or "referencia" in error_detail.lower()

    def test_non_admin_cannot_create(self, client, client_headers, db_session):
        """CLIENT cannot create (403)."""
        self._seed_roles(db_session)

        response = client.post(
            "/api/v1/unidades-medida/",
            json={"nombre": "miligramo", "simbolo": "mg", "tipo": "masa"},
            headers=client_headers,
        )
        assert response.status_code == 403

    def test_unauthenticated_returns_401(self, client, db_session):
        """No auth returns 401."""
        response = client.get("/api/v1/unidades-medida/")
        assert response.status_code == 401

    def test_list_unidades_medida_includes_factor_conversion(self, client, admin_headers, db_session):
        """GET /api/v1/unidades-medida/ returns factor_conversion in each item."""
        self._seed_roles(db_session)
        self._seed_unit(db_session, "kilogramo", "kg", "masa")
        self._seed_unit(db_session, "gramo", "g", "masa")

        response = client.get("/api/v1/unidades-medida/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert all("factor_conversion" in item for item in data), (
            "Every unit must include factor_conversion field"
        )

    def test_get_unidad_medida_by_id_includes_factor_conversion(self, client, admin_headers, db_session):
        """GET /api/v1/unidades-medida/{id} returns factor_conversion."""
        self._seed_roles(db_session)
        unit = self._seed_unit(db_session, "docena", "doc", "unidad")
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
        found = db_session.exec(
            select(UnidadMedida).where(UnidadMedida.nombre == "docena")
        ).first()

        response = client.get(f"/api/v1/unidades-medida/{found.id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "factor_conversion" in data, (
            "Single unit response must include factor_conversion field"
        )

    def test_factor_conversion_default_is_one(self, client, admin_headers, db_session):
        """Units created without an explicit factor default to 1."""
        self._seed_roles(db_session)
        self._seed_unit(db_session, "porcion", "p", "unidad")

        response = client.get("/api/v1/unidades-medida/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        porcion_unit = [u for u in data if u["nombre"] == "porcion"][0]
        assert Decimal(porcion_unit["factor_conversion"]) == Decimal("1"), (
            "factor_conversion should default to 1"
        )

    def test_factor_conversion_non_default_value(self, client, admin_headers, db_session):
        """Units with an explicit factor return that value."""
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
        self._seed_roles(db_session)
        unit = UnidadMedida(nombre="docena", simbolo="doc", tipo="unidad", factor_conversion=12)
        db_session.add(unit)
        db_session.flush()

        response = client.get(f"/api/v1/unidades-medida/{unit.id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["factor_conversion"]) == Decimal("12"), (
            "Explicit factor_conversion=12 should be returned"
        )

    def test_create_with_nombre_too_long_returns_422(self, client, admin_headers, db_session):
        """POST with nombre > 50 chars returns 422 (not 500)."""
        self._seed_roles(db_session)

        long_name = "x" * 51  # Exceeds VARCHAR(50) column limit
        response = client.post(
            "/api/v1/unidades-medida/",
            json={"nombre": long_name, "simbolo": "xxl", "tipo": "unidad"},
            headers=admin_headers,
        )
        assert response.status_code == 422

    def test_create_with_simbolo_too_long_returns_422(self, client, admin_headers, db_session):
        """POST with simbolo > 10 chars returns 422 (not 500)."""
        self._seed_roles(db_session)

        long_simbolo = "x" * 11  # Exceeds VARCHAR(10) column limit
        response = client.post(
            "/api/v1/unidades-medida/",
            json={"nombre": "valido", "simbolo": long_simbolo, "tipo": "unidad"},
            headers=admin_headers,
        )
        assert response.status_code == 422

    def test_create_duplicate_base_unit_returns_409(self, client, admin_headers, db_session):
        """POST a second base unit (factor=1) for same tipo returns 409 Conflict."""
        self._seed_roles(db_session)
        # Seed a base unit for tipo "masa" — gramo with factor_conversion=1
        self._seed_unit(db_session, "gramo", "g", "masa")

        response = client.post(
            "/api/v1/unidades-medida/",
            json={"nombre": "tonelada", "simbolo": "t", "tipo": "masa",
                  "factor_conversion": 1},
            headers=admin_headers,
        )
        assert response.status_code == 409
        detail = response.json().get("detail", "")
        assert "unidad base" in detail.lower()

    def test_create_non_base_unit_for_existing_tipo_succeeds_201(self, client, admin_headers, db_session):
        """POST a non-base unit (factor != 1) for a tipo that already has a base succeeds."""
        self._seed_roles(db_session)
        # Seed a base unit for tipo "masa" — gramo with factor_conversion=1
        self._seed_unit(db_session, "gramo", "g", "masa")

        response = client.post(
            "/api/v1/unidades-medida/",
            json={"nombre": "miligramo", "simbolo": "mg", "tipo": "masa",
                  "factor_conversion": 0.001},
            headers=admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "miligramo"

    def test_update_unit_to_base_when_base_exists_returns_409(self, client, admin_headers, db_session):
        """PUT updating factor_conversion to 1 when a base already exists for that tipo returns 409."""
        self._seed_roles(db_session)
        # Seed base unit for masa (gramo, factor=1) and non-base (kilogramo, factor=1000)
        self._seed_unit(db_session, "gramo", "g", "masa")
        kilo = self._seed_unit(db_session, "kilogramo", "kg", "masa")
        from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
        # Set kilogramo's factor to 1000 (non-base)
        found = db_session.exec(
            select(UnidadMedida).where(UnidadMedida.nombre == "kilogramo")
        ).first()
        found.factor_conversion = 1000
        db_session.flush()

        response = client.put(
            f"/api/v1/unidades-medida/{found.id}",
            json={"factor_conversion": 1},
            headers=admin_headers,
        )
        assert response.status_code == 409
        detail = response.json().get("detail", "")
        assert "unidad base" in detail.lower()
