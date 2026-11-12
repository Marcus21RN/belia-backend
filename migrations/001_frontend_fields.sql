ALTER TABLE clientes
    ADD COLUMN IF NOT EXISTS notas TEXT;

ALTER TABLE citas
    ADD COLUMN IF NOT EXISTS notas_detalles TEXT;

ALTER TABLE citas
    ADD COLUMN IF NOT EXISTS precio_total NUMERIC(10, 2);

ALTER TABLE empleado
    ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE inventario
    ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT TRUE;

CREATE TABLE IF NOT EXISTS cita_detalles (
    id_detalle SERIAL PRIMARY KEY,
    cita_id INTEGER NOT NULL REFERENCES citas(id_cita) ON DELETE CASCADE,
    servicio_id INTEGER NOT NULL REFERENCES servicios(id_servicio),
    empleado_id INTEGER NOT NULL REFERENCES empleado(id_empleado),
    fecha_hora_inicio TIMESTAMP NOT NULL,
    fecha_hora_fin TIMESTAMP NOT NULL,
    CONSTRAINT check_cita_detalle_fechas
        CHECK (fecha_hora_inicio < fecha_hora_fin)
);

CREATE INDEX IF NOT EXISTS ix_cita_detalles_empleado_horario
    ON cita_detalles (empleado_id, fecha_hora_inicio, fecha_hora_fin);
