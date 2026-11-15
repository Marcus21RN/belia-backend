from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models, schemas
from .routers import citas, empleados, paquetes, views
from .routers.crud import crud_router
from .security import verificar_token

app = FastAPI(title="Belia API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://belia.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _crud(model, prefix, tag, name):
    return crud_router(
        model=model,
        prefix=prefix,
        tag=tag,
        create=getattr(schemas, f"{name}Create"),
        update=getattr(schemas, f"{name}Update"),
        out=getattr(schemas, f"{name}Out"),
    )


for router in (
    _crud(models.Cliente, "/clientes", "Clientes", "Cliente"),
    _crud(models.Categoria, "/categorias", "Categorías", "Categoria"),
    _crud(models.Servicio, "/servicios", "Servicios", "Servicio"),
    _crud(models.Inventario, "/inventario", "Inventario", "Inventario"),
    _crud(models.Horario, "/horarios", "Horarios", "Horario"),
    _crud(models.Estado, "/estados", "Estados", "Estado"),
    citas.router,
    paquetes.router,
    views.router,
):
    app.include_router(router, dependencies=[Depends(verificar_token)])
app.include_router(empleados.router)


@app.get("/", tags=["Health"])
def health():
    return {"status": "ok"}


# COMANDO PARA CORRER EL SERVIDOR DE SWAGGER DEL BACKEND ./.venv/bin/python -m uvicorn app.main:app --reload ##
