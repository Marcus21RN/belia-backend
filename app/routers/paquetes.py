from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .crud import commit_or_409, get_or_404

router = APIRouter(prefix="/paquetes", tags=["Paquetes"])


def _set_servicios(obj: models.Paquete, servicios: list[schemas.PaqueteServicioIn]):
    obj.servicios = [
        models.PaqueteServicio(id_servicio=s.id_servicio, notas=s.notas)
        for s in servicios
    ]


@router.get("/", response_model=list[schemas.PaqueteOut])
def listar(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Paquete).offset(skip).limit(min(limit, 500)).all()


@router.get("/{id_paquete}", response_model=schemas.PaqueteOut)
def obtener(id_paquete: int, db: Session = Depends(get_db)):
    return get_or_404(db, models.Paquete, id_paquete)


@router.post("/", response_model=schemas.PaqueteOut, status_code=201)
def crear(data: schemas.PaqueteCreate, db: Session = Depends(get_db)):
    values = data.model_dump(exclude={"servicios"})
    obj = models.Paquete(**values)
    _set_servicios(obj, data.servicios)
    db.add(obj)
    commit_or_409(db)
    db.refresh(obj)
    return obj


@router.patch("/{id_paquete}", response_model=schemas.PaqueteOut)
def actualizar(
    id_paquete: int, data: schemas.PaqueteUpdate, db: Session = Depends(get_db)
):
    obj = get_or_404(db, models.Paquete, id_paquete)
    for k, v in data.model_dump(exclude_unset=True, exclude={"servicios"}).items():
        setattr(obj, k, v)
    if data.servicios is not None:
        _set_servicios(obj, data.servicios)
    commit_or_409(db)
    db.refresh(obj)
    return obj


@router.delete("/{id_paquete}", status_code=204)
def eliminar(id_paquete: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, models.Paquete, id_paquete))
    commit_or_409(db)
