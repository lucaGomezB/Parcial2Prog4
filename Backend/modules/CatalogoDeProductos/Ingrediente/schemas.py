from typing import Optional
from .models import IngredienteBase

class IngredienteCreate(IngredienteBase):
    pass

class IngredienteUpdate(IngredienteBase):
    nombre: Optional[str] = None
    es_alergeno: Optional[bool] = None

class IngredienteRead(IngredienteBase):
    id: int