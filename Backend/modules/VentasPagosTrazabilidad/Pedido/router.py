from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from typing import List
from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import require_roles, get_current_user
from modules.IdentidadYAcceso.Usuario.models import Usuario
from ..HistorialEstadoPedido.models import HistorialEstadoPedido
from ..uow import VentasPagosTrazabilidadUnitOfWork
from .service import PedidoService
from .schemas import (
    PedidoRead, PedidoCreate, PedidoUpdate,
    PedidoAvanzarResponse, PedidoCancelarResponse,
    DetallePedidoUpdate,
)
from ..DetallePedido.models import DetallePedido

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


@router.get("/", response_model=List[PedidoRead],
            dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def read_all(
    skip: int = Query(0),
    limit: int = Query(100),
    session: Session = Depends(get_session),
):
    """List all orders with pagination. Requires ADMIN or PEDIDOS role."""
    return PedidoService.get_all(session, skip=skip, limit=limit)


@router.get("/activos", response_model=List[PedidoRead])
def read_activos(
    skip: int = Query(0),
    limit: int = Query(100),
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """List active (non-terminal) orders. ADMIN/PEDIDOS see all; regular users see only their own."""
    es_gestor = any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in current_user.roles)
    if es_gestor:
        return PedidoService.get_activos(session, skip=skip, limit=limit)
    # Usuario común: solo sus pedidos activos
    todos_activos = PedidoService.get_activos(session, skip=0, limit=10000)
    return [p for p in todos_activos if p.usuario_id == current_user.id][skip:skip + limit]


@router.get("/historial", response_model=List[PedidoRead])
def read_historial(
    skip: int = Query(0),
    limit: int = Query(100),
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """List terminal-state orders (ENTREGADO, CANCELADO). ADMIN/PEDIDOS see all; regular users see only their own."""
    es_gestor = any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in current_user.roles)
    if es_gestor:
        return PedidoService.get_historial(session, skip=skip, limit=limit)
    return PedidoService.get_historial_by_usuario(session, current_user.id, skip=skip, limit=limit)


@router.get("/mis-pedidos", response_model=List[PedidoRead])
def read_mis_pedidos(
    skip: int = Query(0),
    limit: int = Query(100),
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """List orders belonging to the currently authenticated user. Any authenticated user can access."""
    return PedidoService.get_by_usuario_id(session, current_user.id, skip=skip, limit=limit)


@router.get("/{pedido_id}", response_model=PedidoRead)
def read_one(
    pedido_id: int,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """Get a single order by its ID. ADMIN/PEDIDOS can see any; regular users only see their own."""
    obj = PedidoService.get_by_id(session, pedido_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    # Clientes solo ven sus propios pedidos
    if not any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in current_user.roles):
        if obj.usuario_id != current_user.id:
            raise HTTPException(status_code=403, detail="No tienes permiso para ver este pedido")
    return obj


@router.post("/", response_model=PedidoRead, status_code=status.HTTP_201_CREATED)
def create(
    data: PedidoCreate,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
    auto_confirmar: bool = Query(True, description="Auto-advance to CONFIRMADO for client users"),
):
    """Create a new order. Forces the authenticated user as the owner unless ADMIN or PEDIDOS role.
    For non-admin users, the order is auto-advanced to CONFIRMADO when auto_confirmar=True."""
    es_gestor = any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in current_user.roles)

    if data.usuario_id is None:
        data.usuario_id = current_user.id

    pedido = PedidoService.create(session, data)

    # Auto-advance to CONFIRMADO for client users
    if not es_gestor and auto_confirmar:
        try:
            pedido = PedidoService.avanzar_estado(session, pedido.id, current_user)
        except Exception:
            # If auto-advance fails, the order stays in PENDIENTE
            pass

    return pedido


@router.post("/{pedido_id}/avanzar", response_model=PedidoAvanzarResponse,
             dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def avanzar(
    pedido_id: int,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """Advance the order to the next FSM state. Requires ADMIN or PEDIDOS role."""
    pedido = PedidoService.avanzar_estado(session, pedido_id, current_user)
    # Obtener el estado anterior desde el historial (último registro)
    historial = session.exec(
        select(HistorialEstadoPedido)
        .where(HistorialEstadoPedido.pedido_id == pedido_id)
        .order_by(HistorialEstadoPedido.id.desc())
        .limit(1)
    ).first()
    estado_anterior = historial.estado_desde if historial else "DESCONOCIDO"
    return PedidoAvanzarResponse(
        id=pedido.id,
        estado_anterior=estado_anterior,
        estado_actual=pedido.estado_codigo,
        mensaje=f"Pedido avanzó de {estado_anterior} a {pedido.estado_codigo}",
    )


@router.post("/{pedido_id}/cancelar", response_model=PedidoCancelarResponse)
def cancelar(
    pedido_id: int,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """Cancel an order. ADMIN/PEDIDOS always; regular users only before EN_CAMINO."""
    pedido = PedidoService.cancelar_pedido(session, pedido_id, current_user)
    return PedidoCancelarResponse(
        id=pedido.id,
        estado_anterior=pedido.estado_codigo,
        estado_actual="CANCELADO",
        mensaje="Pedido cancelado",
    )


@router.patch("/{pedido_id}", response_model=PedidoRead,
              dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def update(pedido_id: int, data: PedidoUpdate, session: Session = Depends(get_session)):
    """Update an existing order by its ID. Requires ADMIN or PEDIDOS role."""
    obj = PedidoService.update(session, pedido_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return obj


@router.patch("/{pedido_id}/detalles/{producto_id}", response_model=PedidoRead,
              dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def actualizar_detalle(
    pedido_id: int,
    producto_id: int,
    data: DetallePedidoUpdate,
    session: Session = Depends(get_session),
):
    """Update (or remove) a detail line on a PENDIENTE order. cantidad=0 removes it."""
    pedido = PedidoService.get_by_id(session, pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido.estado_codigo != "PENDIENTE":
        raise HTTPException(status_code=400, detail="Solo se pueden modificar detalles en pedidos PENDIENTE")

    with VentasPagosTrazabilidadUnitOfWork(session) as uow:
        stmt = select(DetallePedido).where(
            DetallePedido.pedido_id == pedido_id,
            DetallePedido.producto_id == producto_id,
        )
        detalle = session.exec(stmt).first()
        if not detalle:
            raise HTTPException(status_code=404, detail="Detalle no encontrado en el pedido")

        if data.cantidad <= 0:
            # Eliminar el detalle
            session.delete(detalle)
        else:
            # Actualizar cantidad y subtotal
            detalle.cantidad = data.cantidad
            detalle.subtotal_snap = detalle.precio_snapshot * data.cantidad
            session.add(detalle)

        # Recalcular total del pedido
        detalles_restantes = session.exec(
            select(DetallePedido).where(DetallePedido.pedido_id == pedido_id)
        ).all()
        nuevo_subtotal = sum(d.subtotal_snap for d in detalles_restantes)
        db_pedido = uow.pedidos.get_by_id(pedido_id)
        db_pedido.subtotal = nuevo_subtotal
        db_pedido.total = nuevo_subtotal - db_pedido.descuento + (db_pedido.costo_envio or Decimal('0.00'))
        if db_pedido.total < 0:
            db_pedido.total = Decimal('0.00')
        uow.pedidos.add(db_pedido)
        uow.commit()
        uow.pedidos.refresh(db_pedido)
        return db_pedido


@router.delete("/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(["ADMIN"]))])
def delete(pedido_id: int, session: Session = Depends(get_session)):
    """Soft-delete an order by its ID. Requires ADMIN role."""
    if not PedidoService.soft_delete(session, pedido_id):
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return None
