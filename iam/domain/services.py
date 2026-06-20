"""Servicios de dominio del IAM: regla de autenticacion."""
from typing import Optional

from iam.domain.entities import Device


class AuthService:
    """Un dispositivo esta autenticado si fue hallado en el repositorio."""

    @staticmethod
    def authenticate(device: Optional[Device]) -> bool:
        return device is not None
