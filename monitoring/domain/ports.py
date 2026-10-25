"""Puertos del Monitoring: lo que el dominio necesita del exterior.

El servicio de aplicacion instanciaba sus colaboradores en duro
(`EmfReadingRepository()`, `DeviceRepository()`, `CloudSyncService()`), asi que
no habia manera de ejercitar el caso de uso de ingesta sin una base de datos y
una nube reales. De ahi que este repo llegara a tener cero tests.

Estos Protocol no obligan a heredar: las clases de `infrastructure` ya los
cumplen por firma (structural typing). Sirven para documentar el contrato y
para que los tests puedan inyectar dobles.
"""
from __future__ import annotations

from typing import List, Optional, Protocol

from monitoring.domain.entities import EmfReading


class ReadingRepository(Protocol):
    """Persistencia local de lecturas (SQLite en el edge)."""

    def save(self, reading: EmfReading) -> EmfReading:
        """Guarda la lectura y la devuelve con su identidad asignada."""
        ...

    def latest(self, serial_number: Optional[str] = None, limit: int = 50) -> List[EmfReading]:
        ...


class DeviceDirectory(Protocol):
    """Comprueba que el serial y la API key correspondan a un dispositivo conocido."""

    def find_by_id_and_api_key(self, device_id: str, api_key: str):
        """Devuelve el dispositivo, o None si las credenciales no cuadran."""
        ...


class CloudGateway(Protocol):
    """Sincronizacion con el backend en la nube.

    Es deliberadamente tolerante a fallos: si la nube no responde, el edge
    sigue guardando en local y `sync_reading` devuelve False. Perder la
    conexion no debe costar una lectura.
    """

    def sync_reading(
        self, serial_number: str, level: str, message: str, field_ut: float, plug=None
    ) -> bool:
        ...

    def fetch_desired_plug(self, serial_number: str):
        """Orden del usuario para el rele, o None si no hay ninguna."""
        ...
