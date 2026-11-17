import logging
import os
import warnings
from uuid import uuid4

import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from .crud import commit_or_409, get_or_404

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/inventario", tags=["Inventario"])

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
IMAGE_TYPES = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


def _cloudinary_options() -> dict[str, str]:
    names = {
        "cloud_name": "CLOUDINARY_CLOUD_NAME",
        "api_key": "CLOUDINARY_API_KEY",
        "api_secret": "CLOUDINARY_API_SECRET",
    }
    options = {key: os.getenv(name, "") for key, name in names.items()}
    if not all(options.values()):
        logger.error("La configuración de Cloudinary está incompleta")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Cloudinary no está configurado")
    return options


def _validar_imagen(imagen: UploadFile) -> None:
    expected_format = IMAGE_TYPES.get(imagen.content_type or "")
    if expected_format is None:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Usa una imagen JPEG, PNG o WebP")

    imagen.file.seek(0, 2)
    size = imagen.file.tell()
    imagen.file.seek(0)
    if size > MAX_IMAGE_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "La imagen supera el límite de 5 MiB")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(imagen.file, formats=["JPEG", "PNG", "WEBP"]) as opened:
                if opened.format != expected_format:
                    raise HTTPException(
                        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        "El contenido no coincide con el tipo de imagen",
                    )
                if opened.width * opened.height > MAX_IMAGE_PIXELS:
                    raise HTTPException(
                        status.HTTP_413_CONTENT_TOO_LARGE,
                        "La imagen supera el límite de 25 megapíxeles",
                    )
                opened.verify()
            imagen.file.seek(0)
            with Image.open(imagen.file, formats=[expected_format]) as decoded:
                decoded.load()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Imagen inválida o no admitida") from exc
    finally:
        imagen.file.seek(0)


def _eliminar_subida(public_id: str, options: dict[str, str]) -> None:
    try:
        result = cloudinary.uploader.destroy(
            public_id, resource_type="image", timeout=30, **options
        )
        if result.get("result") not in {"ok", "not found"}:
            logger.error("No se pudo limpiar la imagen de Cloudinary %s", public_id)
    except CloudinaryError as exc:
        logger.error("No se pudo limpiar la imagen de Cloudinary %s: %s", public_id, type(exc).__name__)


@router.put("/{item_id}/imagen", response_model=schemas.InventarioOut)
def subir_imagen(
    item_id: int,
    imagen: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    producto = get_or_404(db, models.Inventario, item_id)
    _validar_imagen(imagen)
    options = _cloudinary_options()
    public_id = f"belia/inventario/{uuid4().hex}"

    try:
        result = cloudinary.uploader.upload(
            imagen.file, public_id=public_id, resource_type="image", overwrite=False,
            timeout=30, **options,
        )
    except CloudinaryError as exc:
        logger.error("Falló la subida a Cloudinary para la imagen %s: %s", public_id, type(exc).__name__)
        _eliminar_subida(public_id, options)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "No se pudo subir la imagen") from exc

    url = result.get("secure_url")
    if not isinstance(url, str) or not url.startswith("https://"):
        logger.error("Cloudinary devolvió una URL inválida para la imagen %s", public_id)
        _eliminar_subida(public_id, options)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Respuesta inválida de Cloudinary")

    producto.imagen_url = url
    try:
        commit_or_409(db)
    except (HTTPException, SQLAlchemyError):
        try:
            db.rollback()
        finally:
            _eliminar_subida(public_id, options)
        raise
    db.refresh(producto)
    return producto
