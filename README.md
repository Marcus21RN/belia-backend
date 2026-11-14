# Belia API

Configura `DATABASE_URL` y `JWT_SECRET_KEY` en el entorno o en `.env`. La clave
JWT debe ser secreta y segura.

`POST /empleados/login` autentica contra la base de datos y entrega un JWT con
`jti` único y vigencia de una hora. En cada solicitud a las rutas de datos envía
`Authorization: Bearer <access_token>`. Se comprueba que el empleado siga activo
y tenga el rol Administrador o Empleado. El login, la salud y la documentación
son públicos. Ambos roles tienen acceso a todas las rutas de datos.

`POST /empleados/logout` recibe el encabezado Bearer y responde 204. Las
revocaciones se guardan en la memoria del proceso, sin modificar el esquema de
la base de datos. **Se pierden al reiniciar y no se comparten entre procesos o
instancias**: usa un solo proceso y ten en cuenta que un token revocado puede
volver a ser válido tras reiniciar, hasta que expire. Los tokens anteriores a
esta actualización no tienen `jti`; es necesario iniciar sesión de nuevo.
