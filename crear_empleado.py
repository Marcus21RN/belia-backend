import os
import sys
import warnings
from getpass import GetPassWarning, getpass

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import SessionLocal
from app.routers.empleados import crear


def crear_empleado(
    db: Session, nombre: str, correo: str, rol: str, password: str
) -> models.Empleado:
    nombre = nombre.strip()
    correo = correo.strip()
    roles = {"administrador": "Administrador", "empleado": "Empleado"}
    rol_normalizado = roles.get(rol.strip().casefold())
    if not nombre or not correo:
        raise ValueError("El nombre y el correo son obligatorios.")
    if rol_normalizado is None:
        raise ValueError("El rol debe ser Administrador o Empleado.")

    estados = db.query(models.Estado).filter_by(nombre="Activo").limit(2).all()
    if len(estados) != 1:
        raise ValueError("Debe existir exactamente un estado llamado Activo.")
    data = schemas.EmpleadoCreate(
        nombre_completo=nombre,
        correo=correo,
        rol=rol_normalizado,
        estado_id=estados[0].id_estado,
        password=password,
    )
    return crear(data, db)


def main() -> int:
    if not os.getenv("DATABASE_URL"):
        print("Configura DATABASE_URL en el entorno o en .env.", file=sys.stderr)
        return 1

    try:
        nombre = input("Nombre completo: ")
        correo = input("Correo: ")
        rol = input("Rol (Administrador o Empleado): ")
        with warnings.catch_warnings():
            warnings.simplefilter("error", GetPassWarning)
            password = getpass("Contraseña: ")
            confirmacion = getpass("Confirma la contraseña: ")
        if password != confirmacion:
            raise ValueError("Las contraseñas no coinciden.")
        with SessionLocal() as db:
            empleado = crear_empleado(db, nombre, correo, rol, password)
            print(f"Empleado creado correctamente. ID: {empleado.id_empleado}")
    except EOFError:
        print("No se pudo leer la entrada desde la terminal.", file=sys.stderr)
        return 1
    except GetPassWarning:
        print("No se pudo leer la contraseña de forma segura desde la terminal.", file=sys.stderr)
        return 1
    except ValidationError as exc:
        for error in exc.errors(include_input=False, include_url=False):
            print(f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except HTTPException as exc:
        print(f"No se pudo crear el empleado: {exc.detail}", file=sys.stderr)
        return 1
    except SQLAlchemyError as exc:
        original = getattr(exc, "orig", exc)
        codigo = getattr(original, "pgcode", None)
        print(
            f"Error de base de datos: {type(original).__name__}"
            + (f" (código {codigo})" if codigo else ""),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
