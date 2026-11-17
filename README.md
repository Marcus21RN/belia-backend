# Belia API

## Requisitos

- Python 3.14.2, la versión utilizada en el entorno actual.
- Git y acceso al repositorio.
- PostgreSQL 16 con la base y los datos de desarrollo de Belia. Puede estar en
  Docker o en un servidor accesible. Para usar Docker localmente, instala y
  ejecuta Docker Desktop.
- Un respaldo de desarrollo compatible, si todavía no tienes la base de datos.
  El repositorio no contiene el esquema completo ni crea las tablas al arrancar.

Los comandos de esta guía se ejecutan desde la raíz del proyecto. No compartas
contraseñas, archivos `.env`, respaldos ni archivos de credenciales mediante Git.

## 1. Crear el entorno virtual

En macOS o Linux, comprueba que `python3` sea Python 3.14.2 y crea el entorno:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
```

Si `python3` corresponde a otra versión, usa la ruta al ejecutable de Python
3.14.2 instalado en tu equipo para crear el entorno.

En Windows con PowerShell:

```powershell
py -3.14 --version
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Comprueba que el entorno activado utiliza la versión esperada e instala las
dependencias:

```bash
python --version
python -m pip install -r requirements.txt
python -m pip check
```

Si PowerShell impide activar el entorno, puedes sustituir `python` en los
comandos siguientes por `.\.venv\Scripts\python.exe`, sin activarlo.


## 2. Configurar las variables de entorno

Crea un archivo `.env` en la raíz del proyecto con este formato y sustituye los
valores entre `<...>`:

```dotenv
DATABASE_URL=postgresql+psycopg2://<usuario>:<contraseña>@<host>:<puerto>/<base>
JWT_SECRET_KEY=<clave-aleatoria-secreta>
```

## 3. Iniciar y comprobar el backend

Con el entorno virtual activado, ejecuta:

```bash
python -m uvicorn app.main:app --reload
```

- Abre [http://127.0.0.1:8000/](http://127.0.0.1:8000/) para comprobar que la
  aplicación responde. Esta ruta no comprueba la conexión a PostgreSQL.
- Abre [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Para detener el servidor, pulsa `Ctrl+C`. El frontend local está permitido desde
`http://localhost:3000` y `http://localhost:5173`.
