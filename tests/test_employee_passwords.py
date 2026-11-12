import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import HTTPException
from pydantic import ValidationError

from app.routers.empleados import hash_password, login, verify_password
from app.schemas import EmpleadoCreate, EmpleadoUpdate, LoginIn


class EmployeePasswordTests(unittest.TestCase):
    def test_bcrypt_hash_and_verification(self):
        stored = hash_password("contraseña segura")
        self.assertTrue(stored.startswith("$2b$"))
        self.assertTrue(verify_password("contraseña segura", stored))
        self.assertFalse(verify_password("contraseña incorrecta", stored))
        self.assertFalse(verify_password("x" * 73, stored))

    def test_legacy_pbkdf2_verification(self):
        digest = hashlib.pbkdf2_hmac("sha256", b"legacy password", b"salt", 200_000)
        stored = f"pbkdf2_sha256$200000$salt${digest.hex()}"
        self.assertTrue(verify_password("legacy password", stored))
        self.assertFalse(verify_password("wrong password", stored))
        self.assertFalse(verify_password("legacy password", stored.replace("pbkdf2_sha256", "other")))
        self.assertFalse(verify_password("legacy password", "pbkdf2_sha256$invalid$salt$digest"))

    def test_create_and_update_reject_passwords_over_72_utf8_bytes(self):
        employee = {
            "nombre_completo": "Prueba",
            "correo": "test@example.com",
            "rol": "admin",
        }
        EmpleadoCreate(**employee, password="á" * 36)
        EmpleadoUpdate(password="á" * 36)
        with self.assertRaises(ValidationError):
            EmpleadoCreate(**employee, password="á" * 37)
        with self.assertRaises(ValidationError):
            EmpleadoUpdate(password="á" * 37)

    def test_login_accepts_valid_active_employee_and_rejects_bad_credentials(self):
        employee = SimpleNamespace(activo=True, password=hash_password("test password"))
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = employee
        self.assertIs(login(LoginIn(correo="test@example.com", password="test password"), db), employee)
        with self.assertRaises(HTTPException) as error:
            login(LoginIn(correo="test@example.com", password="wrong password"), db)
        self.assertEqual(error.exception.status_code, 401)
        employee.activo = False
        with self.assertRaises(HTTPException) as error:
            login(LoginIn(correo="test@example.com", password="test password"), db)
        self.assertEqual(error.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
