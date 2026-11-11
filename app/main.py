from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models, schemas
from .routers import citas, empleados, paquetes
from .routers.crud import crud_router

app = FastAPI(title="Belia API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
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


app.include_router(_crud(models.Cliente, "/clientes", "Clientes", "Cliente"))
app.include_router(_crud(models.Categoria, "/categorias", "Categorías", "Categoria"))
app.include_router(_crud(models.Servicio, "/servicios", "Servicios", "Servicio"))
app.include_router(_crud(models.Inventario, "/inventario", "Inventario", "Inventario"))
app.include_router(_crud(models.Horario, "/horarios", "Horarios", "Horario"))
app.include_router(_crud(models.Estado, "/estados", "Estados", "Estado"))
app.include_router(empleados.router)
app.include_router(citas.router)
app.include_router(paquetes.router)


@app.get("/", tags=["Health"])
def health():
    return {"status": "ok"}


# COMANDO PARA CORRER EL SERVIDOR DE SWAGGER DEL BACKEND ./.venv/bin/python -m uvicorn app.main:app --reload ##
