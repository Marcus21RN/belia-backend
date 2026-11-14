import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db

bearer = HTTPBearer(auto_error=False)
_revocados: dict[str, int] = {}
_revocados_lock = Lock()


@dataclass(frozen=True)
class TokenValidado:
    jti: str
    exp: int


def rol_permitido(rol: str) -> bool:
    return rol.strip().casefold() in {"administrador", "empleado"}


def _clave_jwt() -> str:
    clave = os.getenv("JWT_SECRET_KEY")
    if not clave:
        raise RuntimeError("JWT_SECRET_KEY no está configurada")
    return clave


def crear_token(id_empleado: int) -> str:
    ahora = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(id_empleado),
            "jti": uuid4().hex,
            "iat": ahora,
            "exp": ahora + timedelta(hours=1),
        },
        _clave_jwt(),
        algorithm="HS256",
    )


def _token_invalido() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Token inválido o revocado",
        headers={"WWW-Authenticate": "Bearer"},
    )


def verificar_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> TokenValidado:
    if credentials is None:
        raise _token_invalido()
    try:
        claims = jwt.decode(
            credentials.credentials,
            _clave_jwt(),
            algorithms=["HS256"],
            options={"require": ["sub", "jti", "exp"]},
        )
        jti, exp, sub = claims["jti"], claims["exp"], claims["sub"]
        if (
            not isinstance(jti, str)
            or len(jti) != 32
            or UUID(hex=jti).hex != jti
            or type(exp) is not int
            or not isinstance(sub, str)
            or not sub.isascii()
            or not sub.isdecimal()
            or len(sub) > 10
            or int(sub) < 1
            or int(sub) > 2147483647
        ):
            raise _token_invalido()
    except (jwt.InvalidTokenError, ValueError, TypeError, OverflowError) as exc:
        raise _token_invalido() from exc

    with _revocados_lock:
        if jti in _revocados:
            raise _token_invalido()

    empleado = (
        db.query(models.Empleado)
        .join(models.Estado, models.Estado.id_estado == models.Empleado.estado_id)
        .filter(
            models.Empleado.id_empleado == int(sub),
            models.Estado.nombre == "Activo",
        )
        .first()
    )
    if empleado is None or not rol_permitido(empleado.rol):
        raise _token_invalido()
    return TokenValidado(jti=jti, exp=exp)


def revocar_token(token: TokenValidado) -> None:
    ahora = datetime.now(timezone.utc).timestamp()
    with _revocados_lock:
        for jti, exp in list(_revocados.items()):
            if exp <= ahora:
                del _revocados[jti]
        if token.jti in _revocados:
            raise _token_invalido()
        if token.exp > ahora:
            _revocados[token.jti] = token.exp
