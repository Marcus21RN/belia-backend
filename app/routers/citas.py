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
    q = db.query(models.Cita).filter(
        models.Cita.empleado_id == empleado_id,
        models.Cita.fecha_hora_inicio < fin,
        models.Cita.fecha_hora_fin > inicio,
    )
    if excluir_id is not None:
        q = q.filter(models.Cita.id_cita != excluir_id)
    detalle_q = (
        db.query(models.CitaDetalle)
        .join(models.Cita, models.Cita.id_cita == models.CitaDetalle.cita_id)
        .filter(
            models.CitaDetalle.empleado_id == empleado_id,
            models.CitaDetalle.fecha_hora_inicio < fin,
            models.CitaDetalle.fecha_hora_fin > inicio,
        )
    )
    if excluir_id is not None:
        detalle_q = detalle_q.filter(models.Cita.id_cita != excluir_id)
    if q.first() or detalle_q.first():
        raise HTTPException(
            status.HTTP_409_CONFLICT, "El empleado ya tiene una cita en ese horario"
        )


def _validar_detalles(db, detalles, excluir_id=None):
    vistos = []
    for detalle in detalles:
        _validar_cita(
            db,
            detalle.empleado_id,
            detalle.fecha_hora_inicio,
            detalle.fecha_hora_fin,
            excluir_id,
        )
        for anterior in vistos:
            if (
                anterior.empleado_id == detalle.empleado_id
                and anterior.fecha_hora_inicio < detalle.fecha_hora_fin
                and anterior.fecha_hora_fin > detalle.fecha_hora_inicio
            ):
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "Un especialista no puede tener dos tramos simultáneos en la cita",
                )
        vistos.append(detalle)


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
    values = data.model_dump(exclude={"detalles"})
    if data.detalles:
        _validar_detalles(db, data.detalles)
        first_detail = data.detalles[0]
        values.update(
            empleado_id=first_detail.empleado_id,
            servicio_id=first_detail.servicio_id,
            fecha_hora_inicio=first_detail.fecha_hora_inicio,
            fecha_hora_fin=first_detail.fecha_hora_fin,
        )
    else:
        _validar_cita(
            db, data.empleado_id, data.fecha_hora_inicio, data.fecha_hora_fin
        )
    obj = models.Cita(**values)
    if data.detalles:
        obj.detalles = [
            models.CitaDetalle(**detalle.model_dump()) for detalle in data.detalles
        ]
    db.add(obj)
    commit_or_409(db)
    db.refresh(obj)
    return obj


@router.patch("/{id_cita}", response_model=schemas.CitaOut)
def actualizar(id_cita: int, data: schemas.CitaUpdate, db: Session = Depends(get_db)):
    obj = get_or_404(db, models.Cita, id_cita)
    values = data.model_dump(exclude_unset=True)
    detalles = values.pop("detalles", None)
    for k, v in values.items():
        setattr(obj, k, v)
    if detalles is not None:
        _validar_detalles(db, data.detalles, id_cita)
        if data.detalles:
            first_detail = data.detalles[0]
            obj.empleado_id = first_detail.empleado_id
            obj.servicio_id = first_detail.servicio_id
            obj.fecha_hora_inicio = first_detail.fecha_hora_inicio
            obj.fecha_hora_fin = first_detail.fecha_hora_fin
        obj.detalles = [
            models.CitaDetalle(**detalle.model_dump()) for detalle in data.detalles
        ]
    else:
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
