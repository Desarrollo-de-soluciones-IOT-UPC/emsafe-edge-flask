"""Puertos de SALIDA del bounded context Monitoring.

El caso de uso de ingesta necesita dos cosas del mundo exterior: empujar la lectura
a la nube y traerse la orden del usuario para el rele. Antes las pedia importando
`CloudSyncService` directamente — es decir, la capa de aplicacion conociendo una
clase de infraestructura, con `requests`, URLs y JWT detras. Aqui se declara QUE se
necesita; el COMO vive en `monitoring/infrastructure/cloud_sync.py`.

Es el mismo patron que `ReadingBroadcaster` en el backend, y lo que permite correr
el edge sin nube (o contra un doble de prueba) sin tocar el caso de uso.
"""
from abc import ABC, abstractmethod


class CloudSyncPort(ABC):
    """Contrato del edge con el backend en la nube."""

    @abstractmethod
    def sync_reading(self, reading) -> bool:
        """Reenvia la lectura ya clasificada. True si la nube la acepto."""

    @abstractmethod
    def fetch_desired_plug(self, serial_number):
        """Orden del usuario para el rele: "ON" | "OFF" | None."""
