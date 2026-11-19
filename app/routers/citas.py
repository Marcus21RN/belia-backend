from datetime import datetime
from decimal import Decimal
import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .crud import commit_or_409, flush_or_409, get_or_404

router = APIRouter(prefix="/citas", tags=["Citas"])

def _categoria_especialidad(especialidad):
    valor = "".join(
        c for c in unicodedata.normalize("NFD", (especialidad or "").lower())
        if unicodedata.category(c) != "Mn"
    )
    for expresion, categoria in (
        (r"una|manic|pedic", "unas"),
        (r"color", "coloracion"),
        (r"mirada|ceja|pesta", "mirada"),
        (r"cabell|estilist|corte", "cabello"),
        (r"maquill", "maquillaje"),
        (r"facial", "facial"),
    ):
        if re.search(expresion, valor):
            return categoria
    return None


def _validar_especialista(db, detalle, empleado):
    servicio = get_or_404(db, models.Servicio, detalle.servicio_id)
    categoria = get_or_404(db, models.Categoria, servicio.categoria_id)
    especialidad = _categoria_especialidad(empleado.especialidad)
    categoria_servicio = "".join(
        c for c in unicodedata.normalize("NFD", categoria.nombre.lower())
        if unicodedata.category(c) != "Mn"
    )
    if especialidad != categoria_servicio and not (
        especialidad in ("cabello", "coloracion")
        and categoria_servicio in ("cabello", "coloracion")
    ):
        raise HTTPException(422, f"{empleado.nombre_completo} no tiene la especialidad para {categoria.nombre}")
    estado = db.get(models.Estado, empleado.estado_id)
    if not estado or estado.nombre.lower() != "activo":
        raise HTTPException(422, f"{empleado.nombre_completo} no está activo")
    inicio, fin = detalle.fecha_hora_inicio, detalle.fecha_hora_fin
    dia = (inicio.weekday() + 1) % 7
    horario = db.query(models.Horario).filter(
        models.Horario.empleado_id == empleado.id_empleado,
        models.Horario.dia == dia,
        models.Horario.hora_entrada <= inicio.time(),
        models.Horario.hora_salida >= fin.time(),
    ).first()
    if inicio.date() != fin.date() or not horario:
        raise HTTPException(422, f"{empleado.nombre_completo} no tiene turno para ese horario")


def _selecciones_desde_detalles(detalles):
    return [
        {
            "servicio_id": detalle.servicio_id,
            "paquete_id": None,
            "precio_acordado": None,
            "detalles": [detalle],
        }
        for detalle in detalles
    ]


def _validar_selecciones(db: Session, selecciones):
    for seleccion in selecciones:
        paquete_id = seleccion["paquete_id"]
        if paquete_id is not None:
            get_or_404(db, models.Paquete, paquete_id)
            servicios = {
                row[0]
                for row in db.query(models.PaqueteServicio.id_servicio)
                .filter(models.PaqueteServicio.id_paquete == paquete_id)
                .all()
            }
            ids = [detalle.servicio_id for detalle in seleccion["detalles"]]
            if not servicios or len(ids) != len(servicios) or set(ids) != servicios:
                raise HTTPException(422, "Los tramos deben corresponder a los servicios del paquete")


def _validar_tramos(db: Session, detalles, estado_id, excluir_id=None):
    estado = get_or_404(db, models.Estado, estado_id)
    for anterior, siguiente in zip(detalles, detalles[1:]):
        if anterior.fecha_hora_fin != siguiente.fecha_hora_inicio:
            raise HTTPException(422, "Los tramos deben ser consecutivos y estar ordenados")

    empleados = sorted({detalle.empleado_id for detalle in detalles})
    encontrados = (
        db.query(models.Empleado)
        .filter(models.Empleado.id_empleado.in_(empleados))
        .order_by(models.Empleado.id_empleado)
        .with_for_update()
        .all()
    )
    if len(encontrados) != len(empleados):
        raise HTTPException(422, "Uno o más especialistas no existen")
    if estado.nombre == "Cancelada":
        return

    empleados_por_id = {empleado.id_empleado: empleado for empleado in encontrados}
    for detalle in detalles:
        _validar_especialista(db, detalle, empleados_por_id[detalle.empleado_id])
        conflicto = (
            db.query(models.Cita.id_cita)
            .join(models.Estado, models.Estado.id_estado == models.Cita.estado_id)
            .outerjoin(models.CitaDetalle, models.CitaDetalle.cita_id == models.Cita.id_cita)
            .filter(
                models.Estado.nombre != "Cancelada",
                or_(
                    and_(
                        models.CitaDetalle.empleado_id == detalle.empleado_id,
                        models.CitaDetalle.fecha_hora_inicio < detalle.fecha_hora_fin,
                        models.CitaDetalle.fecha_hora_fin > detalle.fecha_hora_inicio,
                    ),
                    and_(
                        models.CitaDetalle.id_detalle.is_(None),
                        models.Cita.empleado_id == detalle.empleado_id,
                        models.Cita.fecha_hora_inicio < detalle.fecha_hora_fin,
                        models.Cita.fecha_hora_fin > detalle.fecha_hora_inicio,
                    ),
                ),
            )
        )
        if excluir_id is not None:
            conflicto = conflicto.filter(models.Cita.id_cita != excluir_id)
        if conflicto.first():
            raise HTTPException(status.HTTP_409_CONFLICT, "El empleado ya tiene una cita en ese horario")


def _guardar_desglose(db: Session, obj: models.Cita, selecciones):
    db.query(models.CitaDetalle).filter(models.CitaDetalle.cita_id == obj.id_cita).delete()
    db.query(models.CitaSeleccion).filter(models.CitaSeleccion.cita_id == obj.id_cita).delete()
    orden = 0
    for index, seleccion in enumerate(selecciones, 1):
        nueva = models.CitaSeleccion(
            cita_id=obj.id_cita,
            orden=index,
            servicio_id=seleccion["servicio_id"],
            paquete_id=seleccion["paquete_id"],
            precio_acordado=seleccion["precio_acordado"],
        )
        db.add(nueva)
        flush_or_409(db)
        for detalle in seleccion["detalles"]:
            orden += 1
            db.add(
                models.CitaDetalle(
                    cita_id=obj.id_cita,
                    seleccion_id=nueva.id_seleccion,
                    orden=orden,
                    **detalle.model_dump(),
                )
            )
    flush_or_409(db)
    db.expire(obj, ["selecciones", "detalles"])


def _detalles_iguales(actuales, nuevos):
    campos = ("servicio_id", "empleado_id", "fecha_hora_inicio", "fecha_hora_fin")
    return len(actuales) == len(nuevos) and all(
        all(getattr(actual, campo) == getattr(nuevo, campo) for campo in campos)
        for actual, nuevo in zip(actuales, nuevos)
    )


def _preparar_selecciones(db: Session, selecciones, detalles, precio_total):
    if selecciones is not None:
        normalizadas = [
            {
                "servicio_id": seleccion.servicio_id,
                "paquete_id": seleccion.paquete_id,
                "precio_acordado": seleccion.precio_acordado,
                "detalles": seleccion.detalles,
            }
            for seleccion in selecciones
        ]
        precios = [s.precio_acordado for s in selecciones]
        total = sum(precios, Decimal("0")) if all(p is not None for p in precios) else None
        if total is not None and precio_total is not None and precio_total != total:
            raise HTTPException(422, "El precio total no coincide con las selecciones")
        if total is not None:
            precio_total = total
    else:
        normalizadas = _selecciones_desde_detalles(detalles)
    _validar_selecciones(db, normalizadas)
    tramos = [detalle for seleccion in normalizadas for detalle in seleccion["detalles"]]
    return normalizadas, tramos, precio_total


def _sincronizar_cabecera(obj: models.Cita, detalles):
    obj.servicio_id = detalles[0].servicio_id
    obj.empleado_id = detalles[0].empleado_id
    obj.fecha_hora_inicio = detalles[0].fecha_hora_inicio
    obj.fecha_hora_fin = detalles[-1].fecha_hora_fin


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
        q = q.filter(
            or_(
                models.Cita.detalles.any(models.CitaDetalle.empleado_id == empleado_id),
                and_(~models.Cita.detalles.any(), models.Cita.empleado_id == empleado_id),
            )
        )
    if cliente_id:
        q = q.filter(models.Cita.cliente_id == cliente_id)
    if desde:
        q = q.filter(models.Cita.fecha_hora_inicio >= desde)
    if hasta:
        q = q.filter(models.Cita.fecha_hora_inicio <= hasta)
    return q.order_by(models.Cita.fecha_hora_inicio).offset(skip).limit(min(limit, 500)).all()


@router.get("/{id_cita}", response_model=schemas.CitaOut)
def obtener(id_cita: int, db: Session = Depends(get_db)):
    return get_or_404(db, models.Cita, id_cita)


@router.post("/", response_model=schemas.CitaOut, status_code=201)
def crear(data: schemas.CitaCreate, db: Session = Depends(get_db)):
    detalles = data.detalles
    if detalles is None and data.selecciones is None:
        detalles = [schemas.CitaDetalleIn(**data.model_dump(include={
            "servicio_id", "empleado_id", "fecha_hora_inicio", "fecha_hora_fin"
        }))]
    selecciones, tramos, precio_total = _preparar_selecciones(
        db, data.selecciones, detalles, data.precio_total
    )
    _validar_tramos(db, tramos, data.estado_id)
    obj = models.Cita(**data.model_dump(exclude={"selecciones", "detalles", "precio_total"}))
    obj.precio_total = precio_total
    _sincronizar_cabecera(obj, tramos)
    db.add(obj)
    flush_or_409(db)
    _guardar_desglose(db, obj, selecciones)
    commit_or_409(db)
    db.refresh(obj)
    return obj


@router.patch("/{id_cita}", response_model=schemas.CitaOut)
def actualizar(id_cita: int, data: schemas.CitaUpdate, db: Session = Depends(get_db)):
    obj = db.query(models.Cita).filter(models.Cita.id_cita == id_cita).with_for_update().first()
    if obj is None:
        raise HTTPException(404, "Cita no encontrado")
    values = data.model_dump(exclude_unset=True, exclude={"selecciones", "detalles"})
    campos_tramo = {"empleado_id", "servicio_id", "fecha_hora_inicio", "fecha_hora_fin"}
    detalles = data.detalles
    selecciones = data.selecciones
    actuales = list(obj.detalles)

    if detalles is not None and _detalles_iguales(actuales, detalles):
        detalles = None
        for campo in campos_tramo:
            values.pop(campo, None)
        if obj.precio_total is None:
            values.pop("precio_total", None)
    elif detalles is not None and any(s.paquete_id is not None for s in obj.selecciones):
        raise HTTPException(422, "Para modificar los tramos de un paquete envía las selecciones completas")

    if selecciones is None and detalles is None and campos_tramo.intersection(values):
        if len(actuales) > 1:
            raise HTTPException(422, "Para modificar una cita múltiple envía su desglose completo")
        try:
            detalles = [schemas.CitaDetalleIn(**{
                campo: values.get(campo, getattr(obj, campo)) for campo in campos_tramo
            })]
        except ValidationError as exc:
            raise HTTPException(422, "El horario del tramo no es válido") from exc

    nuevo_estado = values.get("estado_id", obj.estado_id)
    if selecciones is not None or detalles is not None:
        normalizadas, tramos, precio_total = _preparar_selecciones(
            db, selecciones, detalles, values.get("precio_total")
        )
        _validar_tramos(db, tramos, nuevo_estado, obj.id_cita)
        for campo in campos_tramo:
            values.pop(campo, None)
        if selecciones is not None:
            values["precio_total"] = precio_total
        _sincronizar_cabecera(obj, tramos)
        _guardar_desglose(db, obj, normalizadas)
    elif "estado_id" in values and values["estado_id"] != obj.estado_id and (
        get_or_404(db, models.Estado, obj.estado_id).nombre == "Cancelada"
    ):
        tramos = [
            schemas.CitaDetalleIn.model_validate(detalle, from_attributes=True)
            for detalle in actuales
        ] or [schemas.CitaDetalleIn.model_validate(obj, from_attributes=True)]
        _validar_tramos(db, tramos, nuevo_estado, obj.id_cita)
    for campo, valor in values.items():
        setattr(obj, campo, valor)
    commit_or_409(db)
    db.refresh(obj)
    return obj


@router.delete("/{id_cita}", status_code=204)
def eliminar(id_cita: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, models.Cita, id_cita))
    commit_or_409(db)
