"""Repositorio del IAM: mapea entre la entidad de dominio y el modelo ORM."""
from typing import Optional

import peewee

from iam.domain.entities import Device
from iam.infrastructure.models import Device as DeviceModel

# Credenciales del dispositivo de prueba (solo desarrollo).
TEST_DEVICE_ID = "EMSAFE-6766-01"
TEST_API_KEY = "emsafe-edge-key-6766"


class DeviceRepository:
    @staticmethod
    def find_by_id_and_api_key(device_id: str, api_key: str) -> Optional[Device]:
        try:
            d = DeviceModel.get(
                (DeviceModel.device_id == device_id) & (DeviceModel.api_key == api_key)
            )
            return Device(d.device_id, d.api_key, d.created_at)
        except peewee.DoesNotExist:
            return None

    @staticmethod
    def get_or_create_test_device() -> Device:
        d, _ = DeviceModel.get_or_create(
            device_id=TEST_DEVICE_ID,
            defaults={"api_key": TEST_API_KEY, "created_at": "2026-06-19T00:00:00Z"},
        )
        return Device(d.device_id, d.api_key, d.created_at)
