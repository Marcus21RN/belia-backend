# Belia Backend

Belia Backend es la API que da soporte a la plataforma de gestión de Belia, un
salón de belleza. Centraliza las operaciones y los datos necesarios para
coordinar citas, clientes, equipo, servicios, paquetes e inventario, y expone
información para las vistas de agenda y panel de control.

## Propósito

Este repositorio contiene la capa de backend que conecta las aplicaciones de
Belia con su base de datos. Proporciona endpoints para consultar y mantener la
información del negocio, aplica reglas operativas y entrega respuestas
estructuradas para las interfaces que consumen la API.

## Funcionalidades principales

- **Citas y agenda:** gestión de citas individuales y de varios servicios,
  incluidos los servicios incluidos en paquetes. Valida horarios de trabajo,
  especialidades del equipo y conflictos de agenda.
- **Clientes y equipo:** consulta y mantenimiento de clientes, empleados,
  roles, estados y horarios de trabajo.
- **Servicios y paquetes:** administración de servicios, categorías, precios,
  duración estimada y paquetes compuestos por varios servicios.
- **Inventario:** gestión de productos, existencias, unidades y presentaciones,
  con soporte para imágenes de productos.
- **Panel y catálogos:** proporciona datos de agenda, indicadores operativos,
  directorios y catálogos para las vistas de la plataforma.
- **Acceso autenticado:** incluye inicio y cierre de sesión para empleados y
  protege las operaciones de gestión mediante tokens de acceso.

## Tecnologías

- **Python** y **FastAPI** para la API HTTP.
- **SQLAlchemy** para el acceso y la persistencia de datos.
- **PostgreSQL** como base de datos.
- **Pydantic** para validar y estructurar los datos de entrada y salida.
- **JWT** para la autenticación de empleados.
- **Cloudinary** para el almacenamiento de imágenes del inventario.

## Organización del código

- `app/main.py`: crea la aplicación y registra los routers.
- `app/models.py` y `app/schemas.py`: definen los modelos de datos y los
  esquemas de la API.
- `app/database.py`: configura la conexión a la base de datos y las sesiones.
- `app/security.py`: gestiona la validación y revocación de tokens.
- `app/routers/`: agrupa las rutas de citas, empleados, inventario, paquetes,
  operaciones CRUD y vistas de agenda, catálogos y panel.

## Alcance

Belia Backend se enfoca en la lógica de servidor y en la exposición de datos
para los clientes de la plataforma. La interfaz de usuario y la infraestructura
de base de datos son componentes separados; la API se integra con PostgreSQL y
con el servicio de imágenes cuando esa funcionalidad se utiliza.
