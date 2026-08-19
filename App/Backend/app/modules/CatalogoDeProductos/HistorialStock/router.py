"""
HistorialStock router — admin endpoint for stock audit trail.
"""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from app.core.database import get_session
from app.core.paginated_response import PaginatedResponse
from app.modules.IdentidadYAcceso.Auth.dependencies import require_roles
from app.core.dependencies import AdminOrStock
from .schemas import HistorialStockRead
from .repository import HistorialStockRepository

router = APIRouter(tags=["stock-historial"])


@router.get(
    "/api/v1/stock/historial/{entidad_tipo}/{entidad_id}",
    response_model=PaginatedResponse[HistorialStockRead],
    dependencies=[Depends(require_roles(AdminOrStock))],
)
def get_stock_historial(
    entidad_tipo: str,
    entidad_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """Return all stock change records for the given entity, newest first.

    Restricted to ADMIN and STOCK roles.
    entidad_tipo must be 'producto' or 'ingrediente'.
    """
    if entidad_tipo not in ("producto", "ingrediente"):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail="entidad_tipo must be 'producto' or 'ingrediente'",
        )

    repo = HistorialStockRepository(session)
    items = repo.get_by_entidad(
        session, entidad_tipo, entidad_id, skip=skip, limit=limit
    )
    # Count total for pagination
    from sqlmodel import select, func
    from .models import HistorialStock
    total = session.exec(
        select(func.count()).select_from(HistorialStock).where(
            HistorialStock.entidad_tipo == entidad_tipo,
            HistorialStock.entidad_id == entidad_id,
        )
    ).one()

    return PaginatedResponse(
        items=[HistorialStockRead.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )
