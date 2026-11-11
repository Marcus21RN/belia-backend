from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Estado(Base):
    __tablename__ = "estado"

    id_estado: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50))


class Cliente(Base):
    __tablename__ = "clientes"

    id_cliente: Mapped[int] = mapped_column(primary_key=True)
    nombre_completo: Mapped[str] = mapped_column(String(150))
    telefono: Mapped[str] = mapped_column(String(15), unique=True)
    correo: Mapped[str | None] = mapped_column(String(100), unique=True)


class Empleado(Base):
    __tablename__ = "empleado"

    id_empleado: Mapped[int] = mapped_column(primary_key=True)
    nombre_completo: Mapped[str] = mapped_column(String(150))
    telefono: Mapped[str | None] = mapped_column(String(15))
    correo: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(255))
    especialidad: Mapped[str | None] = mapped_column(String(100))
    rol: Mapped[str] = mapped_column(String(50))


class Horario(Base):
    __tablename__ = "horarios"
    __table_args__ = (
        CheckConstraint("dia BETWEEN 0 AND 6"),
        CheckConstraint("hora_entrada < hora_salida", name="check_horario_logico"),
    )

    id_horario: Mapped[int] = mapped_column(primary_key=True)
    empleado_id: Mapped[int] = mapped_column(
        ForeignKey("empleado.id_empleado", ondelete="CASCADE")
    )
    dia: Mapped[int] = mapped_column(SmallInteger)
    hora_entrada: Mapped[time]
    hora_salida: Mapped[time]


class Categoria(Base):
    __tablename__ = "categorias"

    id_categoria: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    estado_id: Mapped[int] = mapped_column(ForeignKey("estado.id_estado"))


class Servicio(Base):
    __tablename__ = "servicios"

    id_servicio: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id_categoria"))
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    duracion_estimada: Mapped[int] = mapped_column(SmallInteger)
    notas_detalles: Mapped[str | None] = mapped_column(Text)
    estado_id: Mapped[int] = mapped_column(ForeignKey("estado.id_estado"))


class Presentacion(Base):
    __tablename__ = "presentacion"

    id_presentacion: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)


class UnidadMedida(Base):
    __tablename__ = "unidad_medida"

    id_unidad: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)


class Inventario(Base):
    __tablename__ = "inventario"

    id_producto: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    precio: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    cantidad_existente: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    imagen_url: Mapped[str | None] = mapped_column(Text)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id_categoria"))
    presentacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("presentacion.id_presentacion")
    )
    unidad_id: Mapped[int | None] = mapped_column(ForeignKey("unidad_medida.id_unidad"))


class Cita(Base):
    __tablename__ = "citas"
    __table_args__ = (
        CheckConstraint(
            "fecha_hora_inicio < fecha_hora_fin", name="check_fechas_logicas"
        ),
    )

    id_cita: Mapped[int] = mapped_column(primary_key=True)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleado.id_empleado"))
    servicio_id: Mapped[int] = mapped_column(ForeignKey("servicios.id_servicio"))
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id_cliente"))
    fecha_hora_inicio: Mapped[datetime]
    fecha_hora_fin: Mapped[datetime]
    estado_id: Mapped[int] = mapped_column(ForeignKey("estado.id_estado"))


class Paquete(Base):
    __tablename__ = "paquetes"

    id_paquete: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    descripcion: Mapped[str] = mapped_column(Text)
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    fecha_inicio: Mapped[date]
    fecha_fin: Mapped[date]
    estado_id: Mapped[int] = mapped_column(ForeignKey("estado.id_estado"))

    servicios: Mapped[list["PaqueteServicio"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class PaqueteServicio(Base):
    __tablename__ = "paquete_servicios"

    id_servicio: Mapped[int] = mapped_column(
        ForeignKey("servicios.id_servicio", ondelete="CASCADE"), primary_key=True
    )
    id_paquete: Mapped[int] = mapped_column(
        ForeignKey("paquetes.id_paquete", ondelete="CASCADE"), primary_key=True
    )
    notas: Mapped[str | None] = mapped_column(Text)
