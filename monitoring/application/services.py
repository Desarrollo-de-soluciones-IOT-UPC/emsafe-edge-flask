"""Servicios de aplicacion del Monitoring: orquesta el caso de uso de ingesta."""
from iam.infrastructure.repositories import DeviceRepository
from monitoring.domain.services import EmfReadingService
from monitoring.infrastructure.cloud_sync import CloudSyncService
from monitoring.infrastructure.repositories import EmfReadingRepository


class EmfMonitoringApplicationService:
    def __init__(self):
        self.repository = EmfReadingRepository()
        self.service = EmfReadingService()
        self.device_repository = DeviceRepository()
        self.cloud = CloudSyncService()

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
