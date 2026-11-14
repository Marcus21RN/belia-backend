from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db

router = APIRouter(prefix="/api/v1", tags=["Vistas"])


def _rows(db: Session, statement: str, **params):
    return [dict(row) for row in db.execute(text(statement), params).mappings().all()]


@router.get("/dashboard/kpis")
def dashboard_kpis(db: Session = Depends(get_db)):
    rows = _rows(
        db,
        """
        SELECT
            (SELECT COUNT(*) FROM clientes) AS total_clientes,
            (
                SELECT COUNT(*)
                FROM empleado e
                JOIN estado es ON es.id_estado = e.estado_id
                WHERE es.nombre = 'Activo'
            ) AS empleados_activos,
            (
                SELECT COUNT(*)
                FROM servicios s
                JOIN estado es ON es.id_estado = s.estado_id
                WHERE es.nombre = 'Activo'
            ) AS servicios_activos,
            (
                SELECT COUNT(*)
                FROM citas c
                JOIN estado es ON es.id_estado = c.estado_id
                WHERE c.fecha_hora_inicio::date = CURRENT_DATE
                  AND es.nombre != 'Cancelada'
            ) AS citas_hoy,
            (
                SELECT COALESCE(SUM(s.precio), 0)
                FROM citas c
                JOIN servicios s ON s.id_servicio = c.servicio_id
                JOIN estado es ON es.id_estado = c.estado_id
                WHERE c.fecha_hora_inicio::date = CURRENT_DATE
                  AND es.nombre != 'Cancelada'
            ) AS ingresos_hoy
        """,
    )
    return rows[0] if rows else {}


@router.get("/dashboard/inventario")
def dashboard_inventario(db: Session = Depends(get_db)):
    return _rows(
        db,
        """
        SELECT
            i.id_producto,
            i.nombre,
            i.cantidad_existente,
            i.precio,
            c.nombre AS categoria
        FROM inventario i
        JOIN categorias c ON c.id_categoria = i.categoria_id
        ORDER BY i.cantidad_existente, i.nombre
        """,
    )


@router.get("/dashboard/agenda")
def dashboard_agenda(fecha: date | None = None, db: Session = Depends(get_db)):
    return _rows(
        db,
        """
        SELECT
            c.id_cita,
            c.fecha_hora_inicio::time AS hora_inicio,
            c.fecha_hora_fin::time AS hora_fin,
            s.nombre AS servicio,
            cl.nombre_completo AS cliente,
            e.nombre_completo AS estilista,
            es.nombre AS estado
        FROM citas c
        JOIN servicios s ON c.servicio_id = s.id_servicio
        JOIN clientes cl ON c.cliente_id = cl.id_cliente
        JOIN empleado e ON c.empleado_id = e.id_empleado
        JOIN estado es ON c.estado_id = es.id_estado
        WHERE c.fecha_hora_inicio::date = COALESCE(CAST(:fecha AS date), CURRENT_DATE)
        ORDER BY c.fecha_hora_inicio
        """,
        fecha=fecha,
    )


@router.get("/agenda/citas")
def agenda_citas(
    desde: date | None = None,
    hasta: date | None = None,
    empleado_id: int | None = None,
    cliente_id: int | None = None,
    id_cita: int | None = None,
    db: Session = Depends(get_db),
):
    filters = []
    params = {}
    if desde is not None:
        filters.append("c.fecha_hora_inicio::date >= :desde")
        params["desde"] = desde
    if hasta is not None:
        filters.append("c.fecha_hora_inicio::date <= :hasta")
        params["hasta"] = hasta
    if empleado_id is not None:
        filters.append("c.empleado_id = :empleado_id")
        params["empleado_id"] = empleado_id
    if cliente_id is not None:
        filters.append("c.cliente_id = :cliente_id")
        params["cliente_id"] = cliente_id
    if id_cita is not None:
        filters.append("c.id_cita = :id_cita")
        params["id_cita"] = id_cita
    where_clause = " AND ".join(filters) if filters else "TRUE"

    return _rows(
        db,
        f"""
        SELECT
            c.id_cita,
            c.fecha_hora_inicio::date AS fecha,
            TO_CHAR(c.fecha_hora_inicio, 'HH24:MI') AS hora_inicio,
            TO_CHAR(c.fecha_hora_fin, 'HH24:MI') AS hora_fin,
            c.notas_cita AS specification,
            c.empleado_id,
            e.nombre_completo AS estilista,
            c.servicio_id,
            s.nombre AS servicio,
            s.duracion_estimada,
            s.precio AS precio,
            cat.nombre AS categoria,
            c.cliente_id,
            cl.nombre_completo AS cliente,
            cl.telefono AS telefono_cliente,
            es.nombre AS estado,
            json_build_array(
                json_build_object(
                    'serviceId', s.id_servicio,
                    'serviceName', s.nombre,
                    'category', cat.nombre,
                    'price', s.precio,
                    'durationMinutes', s.duracion_estimada,
                    'startTime', TO_CHAR(c.fecha_hora_inicio, 'HH24:MI'),
                    'endTime', TO_CHAR(c.fecha_hora_fin, 'HH24:MI'),
                    'employeeId', e.id_empleado,
                    'employeeName', e.nombre_completo
                )
            ) AS service_breakdown
        FROM citas c
        JOIN empleado e ON e.id_empleado = c.empleado_id
        JOIN servicios s ON s.id_servicio = c.servicio_id
        JOIN categorias cat ON cat.id_categoria = s.categoria_id
        JOIN clientes cl ON cl.id_cliente = c.cliente_id
        JOIN estado es ON es.id_estado = c.estado_id
        WHERE {where_clause}
        ORDER BY c.fecha_hora_inicio
        """,
        **params,
    )


@router.get("/catalogo/servicios")
def catalogo_servicios(db: Session = Depends(get_db)):
    return _rows(
        db,
        """
        SELECT
            s.id_servicio,
            cat.nombre AS categoria,
            s.nombre AS servicio,
            s.notas_detalles AS notas_detalles,
            s.precio,
            s.duracion_estimada,
            es.id_estado AS estado
        FROM servicios s
        JOIN categorias cat ON cat.id_categoria = s.categoria_id
        JOIN estado es ON es.id_estado = s.estado_id
        ORDER BY cat.nombre, s.nombre
        """,
    )


@router.get("/catalogo/paquetes")
def catalogo_paquetes(db: Session = Depends(get_db)):
    return _rows(
        db,
        """
        SELECT
            p.id_paquete,
            p.nombre AS paquete,
            p.descripcion,
            p.precio,
            p.fecha_inicio,
            p.fecha_fin,
            es.nombre AS estado,
            COALESCE(STRING_AGG(s.nombre, ', ' ORDER BY s.nombre), '') AS servicios_incluidos,
            COALESCE(
                array_agg(ps.id_servicio ORDER BY ps.id_servicio)
                    FILTER (WHERE ps.id_servicio IS NOT NULL),
                ARRAY[]::integer[]
            ) AS servicios_ids,
            COALESCE(SUM(s.duracion_estimada), 0) AS duracion_estimada
        FROM paquetes p
        JOIN estado es ON es.id_estado = p.estado_id
        LEFT JOIN paquete_servicios ps ON ps.id_paquete = p.id_paquete
        LEFT JOIN servicios s ON s.id_servicio = ps.id_servicio
        GROUP BY p.id_paquete, p.nombre, p.descripcion, p.precio,
            p.fecha_inicio, p.fecha_fin, es.nombre
        ORDER BY p.id_paquete
        """,
    )


@router.get("/directorio/empleados")
def directorio_empleados(db: Session = Depends(get_db)):
    return _rows(
        db,
        """
        SELECT
            e.id_empleado,
            e.nombre_completo,
            e.telefono,
            e.correo,
            e.especialidad,
            e.rol,
            es.nombre AS estado
        FROM empleado e
        LEFT JOIN estado es ON es.id_estado = e.estado_id
        ORDER BY e.nombre_completo
        """,
    )


@router.get("/inventario/tabla")
def tabla_inventario(db: Session = Depends(get_db)):
    return _rows(
        db,
        """
        SELECT
            i.id_producto,
            i.nombre,
            i.cantidad_existente,
            i.imagen_url,
            i.precio,
            i.categoria_id,
            i.presentacion_id,
            i.unidad_id,
            c.nombre AS categoria,
            p.nombre AS presentacion,
            um.nombre AS unidad
        FROM inventario i
        JOIN categorias c ON c.id_categoria = i.categoria_id
        LEFT JOIN presentacion p ON p.id_presentacion = i.presentacion_id
        LEFT JOIN unidad_medida um ON um.id_unidad = i.unidad_id
        ORDER BY i.cantidad_existente, i.nombre
        """,
    )


@router.get("/catalogo/referencias")
def catalogo_referencias(db: Session = Depends(get_db)):
    return {
        "categorias": _rows(
            db, "SELECT id_categoria, nombre FROM categorias ORDER BY nombre"
        ),
        "estados": _rows(db, "SELECT id_estado, nombre FROM estado ORDER BY nombre"),
        "presentaciones": _rows(
            db, "SELECT id_presentacion, nombre FROM presentacion ORDER BY nombre"
        ),
        "unidades": _rows(
            db, "SELECT id_unidad, nombre FROM unidad_medida ORDER BY nombre"
        ),
    }
