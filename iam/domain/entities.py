"""Entidades de dominio del bounded context IAM."""
from datetime import datetime


class Device:
    """Aggregate root: dispositivo registrado, autenticado por su API key.

    Attributes:
        device_id (str): Identificador unico del dispositivo
            (en EMSafe es el numero de serie, ej. 'EMSAFE-6766-01').
        api_key (str): Clave secreta enviada en el header 'X-API-Key'.
        created_at (datetime): Fecha de registro.
    """

    def __init__(self, device_id: str, api_key: str, created_at: datetime):
        self.device_id = device_id
        self.api_key = api_key
        self.created_at = created_at
