import hashlib
import hmac
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import TokenValidado, crear_token, revocar_token, rol_permitido, verificar_token
from .crud import commit_or_409, flush_or_409, get_or_404

router = APIRouter(prefix="/empleados", tags=["Empleados"])

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, stored: str) -> bool:
    if stored.startswith(("$2a$", "$2b$", "$2y$")):
        if len(password.encode("utf-8")) > 72:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored.encode("ascii"))
        except (ValueError, UnicodeEncodeError):
            return False
    try:
        algorithm, iters, salt, digest = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters))
    except ValueError:
        return False
    return hmac.compare_digest(check.hex(), digest)


@router.get("/", response_model=list[schemas.EmpleadoOut], dependencies=[Depends(verificar_token)])
def listar(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Empleado).offset(skip).limit(min(limit, 500)).all()


@router.get("/{id_empleado}", response_model=schemas.EmpleadoOut, dependencies=[Depends(verificar_token)])
def obtener(id_empleado: int, db: Session = Depends(get_db)):
    return get_or_404(db, models.Empleado, id_empleado)


@router.post("/", response_model=schemas.EmpleadoOut, status_code=201, dependencies=[Depends(verificar_token)])
def crear(data: schemas.EmpleadoCreate, db: Session = Depends(get_db)):
    values = data.model_dump(exclude={"horarios"})
    values["password"] = hash_password(values["password"])
    obj = models.Empleado(**values)
    db.add(obj)
    flush_or_409(db)
    for horario in data.horarios:
        db.add(models.Horario(empleado_id=obj.id_empleado, **horario.model_dump()))
    commit_or_409(db)
    db.refresh(obj)
    return obj


@router.patch("/{id_empleado}", response_model=schemas.EmpleadoOut, dependencies=[Depends(verificar_token)])
def actualizar(
    id_empleado: int, data: schemas.EmpleadoUpdate, db: Session = Depends(get_db)
):
    obj = get_or_404(db, models.Empleado, id_empleado)
    values = data.model_dump(exclude_unset=True, exclude={"horarios"})
    if values.get("password"):
        values["password"] = hash_password(values["password"])
    for k, v in values.items():
        setattr(obj, k, v)
    if data.horarios is not None:
        db.query(models.Horario).filter_by(empleado_id=id_empleado).delete()
        for horario in data.horarios:
            db.add(models.Horario(empleado_id=id_empleado, **horario.model_dump()))
    commit_or_409(db)
    db.refresh(obj)
    return obj


@router.delete("/{id_empleado}", status_code=204, dependencies=[Depends(verificar_token)])
def eliminar(id_empleado: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, models.Empleado, id_empleado))
    commit_or_409(db)


@router.post("/login", response_model=schemas.LoginOut)
def login(data: schemas.LoginIn, db: Session = Depends(get_db)):
    emp = (
        db.query(models.Empleado)
        .join(models.Estado, models.Estado.id_estado == models.Empleado.estado_id)
        .filter(
            models.Empleado.correo == data.correo,
            models.Estado.nombre == "Activo",
        )
        .first()
    )
    if not emp or not verify_password(data.password, emp.password) or not rol_permitido(emp.rol):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    return {"access_token": crear_token(emp.id_empleado), "token_type": "bearer", "employee": emp}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: TokenValidado = Depends(verificar_token)):
    revocar_token(token)
