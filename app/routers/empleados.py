import hashlib
import hmac
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .crud import commit_or_409, get_or_404

router = APIRouter(prefix="/empleados", tags=["Empleados"])

ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt, digest = stored.split("$")
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters))
    return hmac.compare_digest(check.hex(), digest)


@router.get("/", response_model=list[schemas.EmpleadoOut])
def listar(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Empleado).offset(skip).limit(min(limit, 500)).all()


@router.get("/{id_empleado}", response_model=schemas.EmpleadoOut)
def obtener(id_empleado: int, db: Session = Depends(get_db)):
    return get_or_404(db, models.Empleado, id_empleado)


@router.post("/", response_model=schemas.EmpleadoOut, status_code=201)
def crear(data: schemas.EmpleadoCreate, db: Session = Depends(get_db)):
    values = data.model_dump()
    values["password"] = hash_password(values["password"])
    obj = models.Empleado(**values)
    db.add(obj)
    commit_or_409(db)
    db.refresh(obj)
    return obj


@router.patch("/{id_empleado}", response_model=schemas.EmpleadoOut)
def actualizar(
    id_empleado: int, data: schemas.EmpleadoUpdate, db: Session = Depends(get_db)
):
    obj = get_or_404(db, models.Empleado, id_empleado)
    values = data.model_dump(exclude_unset=True)
    if values.get("password"):
        values["password"] = hash_password(values["password"])
    for k, v in values.items():
        setattr(obj, k, v)
    commit_or_409(db)
    db.refresh(obj)
    return obj


@router.delete("/{id_empleado}", status_code=204)
def eliminar(id_empleado: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, models.Empleado, id_empleado))
    commit_or_409(db)


@router.post("/login", response_model=schemas.EmpleadoOut)
def login(data: schemas.LoginIn, db: Session = Depends(get_db)):
    emp = db.query(models.Empleado).filter_by(correo=data.correo).first()
    if not emp or not verify_password(data.password, emp.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    return emp
