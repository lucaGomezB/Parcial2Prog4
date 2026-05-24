from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field

def get_utc_now():
    # La forma moderna: timezone-aware UTC
    return datetime.now(timezone.utc)

class TimestampModel(SQLModel):
    created_at: datetime = Field(
        default_factory=get_utc_now,
        nullable=False
    )
    
    updated_at: datetime = Field(
        default_factory=get_utc_now,
        sa_column_kwargs={"onupdate": get_utc_now},
        nullable=False
    )

class SoftDeleteModel(SQLModel):
    deleted_at: Optional[datetime] = Field(default=None, index=True) #Si deleted_at es None, el registro (fila) está activo, sino ha sido borrado en cierta ocasión.
    #Filtrado: En cada consulta (SELECT), debemos agregar un filtro: WHERE deleted_at IS NULL, para no seleccionar los registros borrados lógicamente.