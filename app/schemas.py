from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Estado / catálogos simples
class NombreBase(BaseModel):
    nombre: str = Field(max_length=100)


class EstadoCreate(NombreBase):
    pass


class EstadoUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=100)


class EstadoOut(ORM, NombreBase):
    id_estado: int


class PresentacionOut(ORM, NombreBase):
    id_presentacion: int


class UnidadOut(ORM, NombreBase):
    id_unidad: int


# Clientes
class ClienteBase(BaseModel):
    nombre_completo: str = Field(max_length=150)
    telefono: str = Field(max_length=15)
    correo: str | None = Field(None, max_length=100)
    notas: str | None = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nombre_completo: str | None = Field(None, max_length=150)
    telefono: str | None = Field(None, max_length=15)
    correo: str | None = Field(None, max_length=100)
    notas: str | None = None


class ClienteOut(ORM, ClienteBase):
    id_cliente: int


# Empleados (el password nunca se devuelve)
class EmpleadoBase(BaseModel):
    nombre_completo: str = Field(max_length=150)
    telefono: str | None = Field(None, max_length=15)
    correo: str = Field(max_length=100)
    especialidad: str | None = Field(None, max_length=100)
    rol: str = Field(max_length=50)
    estado_id: int | None = None


class HorarioEmpleadoIn(BaseModel):
    dia: int = Field(ge=0, le=6, description="0=Domingo, 6=Sábado")
    hora_entrada: time
    hora_salida: time

    @model_validator(mode="after")
    def _validar_horas(self):
        if self.hora_entrada >= self.hora_salida:
            raise ValueError("hora_entrada debe ser menor que hora_salida")
        return self


def validar_password_bcrypt(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("La contraseña no puede superar 72 bytes en UTF-8.")
    return password


class EmpleadoCreate(EmpleadoBase):
    password: str = Field(min_length=8, max_length=128)
    horarios: list[HorarioEmpleadoIn] = Field(default_factory=list)

    @field_validator("password")
    @classmethod
    def validar_password(cls, password: str) -> str:
        return validar_password_bcrypt(password)


class EmpleadoUpdate(BaseModel):
    nombre_completo: str | None = Field(None, max_length=150)
    telefono: str | None = Field(None, max_length=15)
    correo: str | None = Field(None, max_length=100)
    especialidad: str | None = Field(None, max_length=100)
    rol: str | None = Field(None, max_length=50)
    estado_id: int | None = None
    password: str | None = Field(None, min_length=8, max_length=128)
    horarios: list[HorarioEmpleadoIn] | None = None

    @field_validator("password")
    @classmethod
    def validar_password(cls, password: str | None) -> str | None:
        return validar_password_bcrypt(password) if password is not None else None


class EmpleadoOut(ORM, EmpleadoBase):
    id_empleado: int


class LoginIn(BaseModel):
    correo: str
    password: str


class LoginEmployeeOut(ORM):
    id_empleado: int
    nombre_completo: str
    correo: str
    rol: str
    especialidad: str | None = None
    telefono: str | None = None


class LoginOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    employee: LoginEmployeeOut


# Horarios
class HorarioBase(BaseModel):
    empleado_id: int
    dia: int = Field(ge=0, le=6, description="0=Domingo, 6=Sábado")
    hora_entrada: time
    hora_salida: time

    @model_validator(mode="after")
    def _validar_horas(self):
        if self.hora_entrada >= self.hora_salida:
            raise ValueError("hora_entrada debe ser menor que hora_salida")
        return self


class HorarioCreate(HorarioBase):
    pass


class HorarioUpdate(BaseModel):
    dia: int | None = Field(None, ge=0, le=6)
    hora_entrada: time | None = None
    hora_salida: time | None = None


class HorarioOut(ORM, HorarioBase):
    id_horario: int


# Categorías
class CategoriaBase(BaseModel):
    nombre: str = Field(max_length=100)
    estado_id: int


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=100)
    estado_id: int | None = None


class CategoriaOut(ORM, CategoriaBase):
    id_categoria: int


# Servicios
class ServicioBase(BaseModel):
    nombre: str = Field(max_length=150)
    categoria_id: int
    precio: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    duracion_estimada: int = Field(gt=0, description="Minutos")
    notas_detalles: str | None = None
    estado_id: int


class ServicioCreate(ServicioBase):
    pass


class ServicioUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=150)
    categoria_id: int | None = None
    precio: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    duracion_estimada: int | None = Field(None, gt=0)
    notas_detalles: str | None = None
    estado_id: int | None = None


class ServicioOut(ORM, ServicioBase):
    id_servicio: int


# Inventario
class InventarioBase(BaseModel):
    nombre: str = Field(max_length=150)
    precio: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    cantidad_existente: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    imagen_url: str | None = None
    categoria_id: int
    presentacion_id: int | None = None
    estado_id: int
    unidad_id: int | None = None


class InventarioCreate(InventarioBase):
    pass


class InventarioUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=150)
    precio: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    cantidad_existente: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    imagen_url: str | None = None
    categoria_id: int | None = None
    presentacion_id: int | None = None
    estado_id: int | None = None
    unidad_id: int | None = None


class InventarioOut(ORM, InventarioBase):
    id_producto: int


# Citas
class CitaDetalleIn(BaseModel):
    servicio_id: int
    empleado_id: int
    fecha_hora_inicio: datetime
    fecha_hora_fin: datetime

    @model_validator(mode="after")
    def _validar_fechas(self):
        if self.fecha_hora_inicio.tzinfo or self.fecha_hora_fin.tzinfo:
            raise ValueError("Los horarios deben ser locales y no incluir zona horaria")
        if self.fecha_hora_inicio >= self.fecha_hora_fin:
            raise ValueError("fecha_hora_inicio debe ser menor que fecha_hora_fin")
        return self


class CitaSeleccionIn(BaseModel):
    servicio_id: int | None = None
    paquete_id: int | None = None
    precio_acordado: Decimal | None = Field(ge=0, max_digits=10, decimal_places=2)
    detalles: list[CitaDetalleIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _validar_seleccion(self):
        if (self.servicio_id is None) == (self.paquete_id is None):
            raise ValueError("Indica un servicio o un paquete, no ambos")
        if self.servicio_id is not None and (
            len(self.detalles) != 1
            or self.detalles[0].servicio_id != self.servicio_id
        ):
            raise ValueError("La selección de servicio debe contener su único tramo")
        return self


class CitaDetalleOut(ORM, CitaDetalleIn):
    id_detalle: int
    seleccion_id: int
    orden: int


class CitaSeleccionOut(ORM):
    id_seleccion: int
    orden: int
    servicio_id: int | None
    paquete_id: int | None
    precio_acordado: Decimal | None
    detalles: list[CitaDetalleOut]


class CitaBase(BaseModel):
    empleado_id: int
    servicio_id: int
    cliente_id: int
    fecha_hora_inicio: datetime
    fecha_hora_fin: datetime
    estado_id: int
    notas_cita: str | None = None

    @model_validator(mode="after")
    def _validar_fechas(self):
        if self.fecha_hora_inicio >= self.fecha_hora_fin:
            raise ValueError("fecha_hora_inicio debe ser menor que fecha_hora_fin")
        return self


class CitaCreate(CitaBase):
    precio_total: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    selecciones: list[CitaSeleccionIn] | None = Field(None, min_length=1)
    detalles: list[CitaDetalleIn] | None = Field(None, min_length=1)

    @model_validator(mode="after")
    def _validar_formato(self):
        if self.selecciones is not None and self.detalles is not None:
            raise ValueError("Usa selecciones o detalles, no ambos")
        return self


class CitaUpdate(BaseModel):
    empleado_id: int | None = None
    servicio_id: int | None = None
    cliente_id: int | None = None
    fecha_hora_inicio: datetime | None = None
    fecha_hora_fin: datetime | None = None
    estado_id: int | None = None
    notas_cita: str | None = None
    precio_total: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    selecciones: list[CitaSeleccionIn] | None = Field(None, min_length=1)
    detalles: list[CitaDetalleIn] | None = Field(None, min_length=1)

    @model_validator(mode="after")
    def _validar_formato(self):
        if self.selecciones is not None and self.detalles is not None:
            raise ValueError("Usa selecciones o detalles, no ambos")
        for field in ("empleado_id", "servicio_id", "cliente_id", "fecha_hora_inicio", "fecha_hora_fin", "estado_id", "selecciones", "detalles"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} no puede ser nulo")
        return self


class CitaOut(ORM, CitaBase):
    id_cita: int
    precio_total: Decimal | None
    selecciones: list[CitaSeleccionOut]
    detalles: list[CitaDetalleOut]


# Paquetes
class PaqueteServicioIn(BaseModel):
    id_servicio: int
    notas: str | None = None


class PaqueteServicioOut(ORM, PaqueteServicioIn):
    pass


class PaqueteBase(BaseModel):
    nombre: str = Field(max_length=150)
    descripcion: str
    precio: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    fecha_inicio: date
    fecha_fin: date
    estado_id: int


class PaqueteCreate(PaqueteBase):
    servicios: list[PaqueteServicioIn] = []


class PaqueteUpdate(BaseModel):
    nombre: str | None = Field(None, max_length=150)
    descripcion: str | None = None
    precio: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    estado_id: int | None = None
    servicios: list[PaqueteServicioIn] | None = None


class PaqueteOut(ORM, PaqueteBase):
    id_paquete: int
    servicios: list[PaqueteServicioOut] = []
