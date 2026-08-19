"""
Categoria router — API endpoints for category management.

Endpoints:
    GET /tree        — Category hierarchy tree (public)
    GET /            — List categories with filters (public)
    GET /{id}        — Single category (public)
    POST /           — Create category (ADMIN only)
    PATCH /{id}      — Update category (ADMIN only)
    DELETE /{id}     — Soft-delete category (ADMIN only)

Prefix: /categorias
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from sqlmodel import Session
from app.core.database import get_session
from app.core.paginated_response import PaginatedResponse
from app.core.dependencies import AdminOnly
from app.core.routing import get_or_404
from app.modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .service import CategoriaService
from .schemas import CategoriaRead, CategoriaCreate, CategoriaTree, CategoriaUpdate

router = APIRouter(prefix="/categorias", tags=["Categorías"])

@router.get("/tree", response_model=list[CategoriaTree])
def get_tree(session: Session = Depends(get_session)):
    """GET /categorias/tree — Get the category tree (root categories with nested children). Public endpoint."""
    return CategoriaService.get_root_categories(session)

# Lo usamos para debugging
@router.get("/", response_model=PaginatedResponse[CategoriaRead])
def read_categorias(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    parent_id: Optional[int] = Query(None, description="Filter by parent category ID"),
    session: Session = Depends(get_session),
):
    """GET /categorias — List all categories with pagination and optional parent_id filter. Public endpoint."""
    return CategoriaService.get_all(session, skip=skip, limit=limit, parent_id=parent_id)

@router.get("/{categoria_id}", response_model=CategoriaRead)
def read_categoria(categoria_id: int, session: Session = Depends(get_session)):
    """GET /categorias/{id} — Get a single category by its ID. Public endpoint."""
    categoria = CategoriaService.get_by_id(session, categoria_id)
    return get_or_404(categoria, "No encontrada")

# Protected endpoints — ADMIN only
@router.post("/", response_model=CategoriaRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles(AdminOnly))])
def create_categoria(data: CategoriaCreate, session: Session = Depends(get_session)):
    """POST /categorias — Create a new category. Requires ADMIN role."""
    return CategoriaService.create(session, data)

@router.patch("/{categoria_id}", response_model=CategoriaRead, dependencies=[Depends(require_roles(AdminOnly))])
def update_categoria(categoria_id: int, data: CategoriaUpdate, session: Session = Depends(get_session)):
    """PATCH /categorias/{id} — Update an existing category by ID. Requires ADMIN role."""
    categoria = CategoriaService.update(session, categoria_id, data)
    return get_or_404(categoria, "No encontrada")

@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT,
                dependencies=[Depends(require_roles(AdminOnly))])
def delete_categoria(categoria_id: int, session: Session = Depends(get_session)):
    """DELETE /categorias/{id} — Soft-delete a category by ID. Requires ADMIN role."""
    obj = CategoriaService.soft_delete(session, categoria_id)
    get_or_404(obj, "No encontrada")
    return None
