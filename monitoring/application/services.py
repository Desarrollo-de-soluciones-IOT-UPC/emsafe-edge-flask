"""Servicios de aplicacion del Monitoring: orquesta el caso de uso de ingesta."""
from typing import Optional

from iam.infrastructure.repositories import DeviceRepository
from monitoring.domain.ports import CloudGateway, DeviceDirectory, ReadingRepository
from monitoring.domain.services import EmfReadingService
from monitoring.infrastructure.cloud_sync import CloudSyncService
from monitoring.infrastructure.repositories import EmfReadingRepository


class EmfMonitoringApplicationService:
    """Caso de uso: el edge recibe una lectura, la clasifica, la guarda y sincroniza.

    Los colaboradores se inyectan. Antes se instanciaban en duro aqui dentro,
    lo que obligaba a tener SQLite y la nube levantadas para ejercitar el caso
    de uso; por eso no habia tests. Los valores por defecto mantienen el
    comportamiento de produccion intacto.
    """

    def __init__(
        self,
        repository: Optional[ReadingRepository] = None,
        device_directory: Optional[DeviceDirectory] = None,
        cloud: Optional[CloudGateway] = None,
        service: Optional[EmfReadingService] = None,
    ) -> None:
        self.repository = repository or EmfReadingRepository()
        self.device_repository = device_directory or DeviceRepository()
        self.cloud = cloud or CloudSyncService()
        self.service = service or EmfReadingService()

    def create_reading(self, serial_number, field_ut, plug, created_at, api_key):
        """1) valida identidad  2) clasifica+valida  3) persiste local
        4) sincroniza nube  5) trae la orden del usuario para el rele (si hay)."""
        if not self.device_repository.find_by_id_and_api_key(serial_number, api_key):
            raise ValueError("Device not found")
        reading = self.service.create_reading(serial_number, field_ut, plug, created_at)
        saved = self.repository.save(reading)
        synced = self.cloud.sync_reading(
            saved.serial_number, saved.level, saved.message, saved.field_ut, saved.plug
        )
        desired_plug = self.cloud.fetch_desired_plug(saved.serial_number)
        print(f"[EDGE] {saved.serial_number} | {saved.field_ut} uT | {saved.level} | "
              f"plug={saved.plug} | desired={desired_plug} | synced={synced}")
        return saved, synced, desired_plug

    def list_readings(self, serial_number=None, limit=50):
        return self.repository.latest(serial_number, limit)
