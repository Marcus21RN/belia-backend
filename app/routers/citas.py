from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .crud import commit_or_409, get_or_404

router = APIRouter(prefix="/citas", tags=["Citas"])


def _validar_cita(db: Session, empleado_id, inicio, fin, excluir_id=None):
    if inicio >= fin:
        raise HTTPException(422, "fecha_hora_inicio debe ser menor que fecha_hora_fin")
    q = (
        db.query(models.Cita)
        .join(models.Estado, models.Estado.id_estado == models.Cita.estado_id)
        .filter(
            models.Cita.empleado_id == empleado_id,
            models.Cita.fecha_hora_inicio < fin,
            models.Cita.fecha_hora_fin > inicio,
            models.Estado.nombre != "Cancelada",
        )
    )
    if excluir_id is not None:
        q = q.filter(models.Cita.id_cita != excluir_id)

    if q.first():
        raise HTTPException(
            status.HTTP_409_CONFLICT, "El empleado ya tiene una cita en ese horario"
        )


@router.get("/", response_model=list[schemas.CitaOut])
def listar(
    empleado_id: int | None = None,
    cliente_id: int | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(models.Cita)
    if empleado_id:
        q = q.filter(models.Cita.empleado_id == empleado_id)
    if cliente_id:
        q = q.filter(models.Cita.cliente_id == cliente_id)
    if desde:
        q = q.filter(models.Cita.fecha_hora_inicio >= desde)
    if hasta:
        q = q.filter(models.Cita.fecha_hora_inicio <= hasta)
    return (
        q.order_by(models.Cita.fecha_hora_inicio).offset(skip).limit(min(limit, 500)).all()
    )


@router.get("/{id_cita}", response_model=schemas.CitaOut)
def obtener(id_cita: int, db: Session = Depends(get_db)):
    return get_or_404(db, models.Cita, id_cita)


@router.post("/", response_model=schemas.CitaOut, status_code=201)
def crear(data: schemas.CitaCreate, db: Session = Depends(get_db)):
    _validar_cita(db, data.empleado_id, data.fecha_hora_inicio, data.fecha_hora_fin)
    obj = models.Cita(**data.model_dump())
    db.add(obj)
    commit_or_409(db)
    db.refresh(obj)
    return obj


@router.patch("/{id_cita}", response_model=schemas.CitaOut)
def actualizar(id_cita: int, data: schemas.CitaUpdate, db: Session = Depends(get_db)):
    obj = get_or_404(db, models.Cita, id_cita)
    values = data.model_dump(exclude_unset=True)
    for k, v in values.items():
        setattr(obj, k, v)
    _validar_cita(
        db, obj.empleado_id, obj.fecha_hora_inicio, obj.fecha_hora_fin, id_cita
    )
    commit_or_409(db)
    db.refresh(obj)
    return obj


@router.delete("/{id_cita}", status_code=204)
def eliminar(id_cita: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, models.Cita, id_cita))
    commit_or_409(db)
