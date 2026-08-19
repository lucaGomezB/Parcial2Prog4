"""
Producto schemas — Pydantic models for API request/response validation.

These schemas define the shape of data entering (Create, Update) and
leaving (Read) the API for the Product entity.
"""
from typing import Optional, List
from decimal import Decimal
from pydantic import ConfigDict, field_validator
from sqlmodel import Field, SQLModel


class IngredienteAsignado(SQLModel):
    """Payload for assigning an ingredient to a product with metadata."""
    ingrediente_id: int = 0
    cantidad: Decimal = Field(default=Decimal("1"), max_digits=10, decimal_places=3)
    es_removible: bool = True
    es_principal: bool = False
    orden: int = 0
    unidad_medida_id: Optional[int] = None


class CategoriaAsignada(SQLModel):
    """Payload for assigning a category to a product."""
    categoria_id: int
    es_principal: bool = False


class ProductoCreate(SQLModel):
    """Request schema for creating a new product.

    At least one category is required (validated by validar_categorias).
    The optional categoria_principal_id marks one category as primary.
    """
    nombre: str
    descripcion: Optional[str] = None
    receta: Optional[str] = None
    precio_base: Decimal = Decimal('0.00')
    precio_actual: Optional[Decimal] = None
    imagenes_url: List[str] = []
    tiempo_prep_min: int = 0
    disponible: bool = True
    es_producto_terminado: bool = False
    categorias_ids: List[int] = []
    categoria_principal_id: Optional[int] = None
    ingredientes: Optional[List[IngredienteAsignado]] = []
    unidad_medida_id: Optional[int] = None

    @field_validator('categorias_ids')
    @classmethod
    def validar_categorias(cls, v):
        """Business rule: a product must belong to at least one category."""
        if not v or len(v) == 0:
            raise ValueError('Se requiere al menos 1 categoría para crear un producto')
        return v


class ProductoUpdate(SQLModel):
    """Request schema for updating an existing product.

    All fields are optional — only provided fields will be applied.
    """
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    receta: Optional[str] = None
    precio_base: Optional[Decimal] = None
    precio_actual: Optional[Decimal] = None
    tiempo_prep_min: Optional[int] = None
    disponible: Optional[bool] = None
    es_producto_terminado: Optional[bool] = None
    imagenes_url: Optional[List[str]] = None
    categorias_ids: Optional[List[int]] = None
    unidad_medida_id: Optional[int] = None
    stock_cantidad: Optional[int] = None
    ingredientes: Optional[List[IngredienteAsignado]] = None


class ProductoRead(SQLModel):
    """Response schema for reading a product.

    tiene_ingredientes is a computed boolean (not a DB column) indicating
    whether the product has any ingredient associations.
    """
    id: int
    nombre: str
    descripcion: Optional[str] = None
    receta: Optional[str] = None
    precio_base: Decimal
    precio_actual: Decimal
    imagenes_url: List[str] = []
    stock_cantidad: int = 0
    tiempo_prep_min: int = 0
    disponible: bool = True
    es_producto_terminado: bool = False
    tiene_ingredientes: bool = False
    categoria_ids: list[int] = Field(default_factory=list)
    unidad_medida_id: Optional[int] = None
    unidad_medida_simbolo: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

    @field_validator("imagenes_url", mode="before")
    @classmethod
    def normalize_imagenes_url(cls, v):
        """DB may store NULL in imagenes_url — convert to empty list for type safety."""
        if v is None:
            return []
        return v


class ProductoIngredienteRead(SQLModel):
    """Response schema for an ingredient associated with a product.

    Includes data from the link table (cantidad, es_removible, orden)
    plus the ingredient's name and allergen flag (joined from Ingrediente table),
    and the unit of measure data (joined from UnidadMedida table).
    """
    ingrediente_id: int
    ingrediente_nombre: str
    cantidad: Decimal
    es_removible: bool
    es_principal: bool
    orden: int
    es_alergeno: bool
    unidad_medida_id: Optional[int] = None
    unidad_medida_simbolo: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ProductoCategoriaRead(SQLModel):
    """Response schema for a category associated with a product."""
    categoria_id: int
    categoria_nombre: str
    es_principal: bool
    model_config = ConfigDict(from_attributes=True)


class IngredienteStockDetail(SQLModel):
    """Per-ingredient stock breakdown for a product's derived stock.

    Shows which ingredients are limiting production and the deficit needed
    to produce at least 1 unit of the product.
    """
    ingrediente_id: int
    ingrediente_nombre: str
    stock_actual: int
    cantidad_receta: Decimal
    cantidad_convertida: Decimal
    unidad_medida_simbolo: Optional[str] = None
    producible: int
    es_limitante: bool
    deficit: int = 0  # stock needed to reach 1 producible unit (0 if already >=1)


class ProductoIngredientesCompartidos(SQLModel):
    """Response: a product and the ingredient names it shares with other products.

    Used by the admin view to warn that a product's derived stock can be
    reduced by other products consuming the same ingredient.
    """
    producto_id: int
    ingredientes: List[str] = []
