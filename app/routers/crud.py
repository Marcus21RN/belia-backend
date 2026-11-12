from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db


def commit_or_409(db: Session):
    """Commit y traduce violaciones de integridad (UNIQUE, FK, CHECK) a 409."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Conflicto de integridad: {exc.orig}"
        ) from exc


def flush_or_409(db: Session):
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Conflicto de integridad: {exc.orig}"
        ) from exc


def get_or_404(db: Session, model, pk):
    obj = db.get(model, pk)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} no encontrado")
    return obj


def crud_router(*, model, prefix: str, tag: str, create, update, out) -> APIRouter:
    """Router CRUD genérico para tablas con llave primaria simple."""
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.get("/", response_model=list[out])
    def listar(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
        return db.query(model).offset(skip).limit(min(limit, 500)).all()

    @router.get("/{item_id}", response_model=out)
    def obtener(item_id: int, db: Session = Depends(get_db)):
        return get_or_404(db, model, item_id)

    @router.post("/", response_model=out, status_code=status.HTTP_201_CREATED)
    def crear(data: create, db: Session = Depends(get_db)):
        obj = model(**data.model_dump())
        db.add(obj)
        commit_or_409(db)
        db.refresh(obj)
        return obj

    @router.patch("/{item_id}", response_model=out)
    def actualizar(item_id: int, data: update, db: Session = Depends(get_db)):
        obj = get_or_404(db, model, item_id)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        commit_or_409(db)
        db.refresh(obj)
        return obj

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def eliminar(item_id: int, db: Session = Depends(get_db)):
        db.delete(get_or_404(db, model, item_id))
        commit_or_409(db)

    return router
