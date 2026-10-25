"""Tests del caso de uso de ingesta, con dobles en lugar de SQLite y la nube.

Esto es lo que los puertos hacen posible: antes el servicio de aplicacion
instanciaba `EmfReadingRepository`, `DeviceRepository` y `CloudSyncService` en
su propio `__init__`, asi que no habia forma de ejercitar la ingesta sin base
de datos ni red.
"""
import unittest

from monitoring.application.services import EmfMonitoringApplicationService

SERIAL = "EMSAFE-6766-01"
API_KEY = "emsafe-edge-key-6766"


class FakeRepository:
    """Repositorio en memoria. Asigna identidad como lo haria SQLite."""

    def __init__(self):
        self.saved = []

    def save(self, reading):
        reading.id = len(self.saved) + 1
        self.saved.append(reading)
        return reading

    def latest(self, serial_number=None, limit=50):
        rows = [r for r in self.saved if not serial_number or r.belongs_to(serial_number)]
        return list(reversed(rows))[:limit]


class FakeDirectory:
    """Acepta solo la pareja serial + api key que se le configure."""

    def __init__(self, serial=SERIAL, api_key=API_KEY):
        self.serial, self.api_key = serial, api_key

    def find_by_id_and_api_key(self, device_id, api_key):
        if device_id == self.serial and api_key == self.api_key:
            return object()
        return None


class FakeCloud:
    """Nube configurable: puede estar caida o devolver una orden para el rele."""

    def __init__(self, reachable=True, desired_plug=None):
        self.reachable, self.desired_plug = reachable, desired_plug
        self.synced = []

    def sync_reading(self, serial_number, level, message, field_ut, plug=None):
        if not self.reachable:
            return False
        self.synced.append((serial_number, level, field_ut, plug))
        return True

    def fetch_desired_plug(self, serial_number):
        return self.desired_plug


def build(cloud=None, directory=None, repository=None):
    return EmfMonitoringApplicationService(
        repository=repository or FakeRepository(),
        device_directory=directory or FakeDirectory(),
        cloud=cloud or FakeCloud(),
    )


class IngestTest(unittest.TestCase):
    def test_guarda_clasifica_y_sincroniza(self):
        repo, cloud = FakeRepository(), FakeCloud()
        service = build(repository=repo, cloud=cloud)

        saved, synced, desired = service.create_reading(SERIAL, 275.0, "ON", None, API_KEY)

        self.assertEqual(saved.level, "DANGER")
        self.assertEqual(saved.id, 1)
        self.assertEqual(len(repo.saved), 1)
        self.assertTrue(synced)
        self.assertEqual(cloud.synced[0][1], "DANGER")

    def test_rechaza_credenciales_desconocidas(self):
        service = build(directory=FakeDirectory(api_key="otra-key"))

        with self.assertRaises(ValueError) as ctx:
            service.create_reading(SERIAL, 50.0, None, None, API_KEY)
        # El endpoint traduce este mensaje a un 404: no cambiarlo.
        self.assertEqual(str(ctx.exception), "Device not found")

    def test_no_guarda_nada_si_la_identidad_no_cuadra(self):
        repo = FakeRepository()
        service = build(repository=repo, directory=FakeDirectory(api_key="otra-key"))

        with self.assertRaises(ValueError):
            service.create_reading(SERIAL, 50.0, None, None, API_KEY)

        self.assertEqual(repo.saved, [])

    def test_si_la_nube_esta_caida_la_lectura_NO_se_pierde(self):
        # Invariante del edge: funciona sin conexion. Guarda en local y avisa
        # de que no sincronizo, pero jamas descarta el dato.
        repo = FakeRepository()
        service = build(repository=repo, cloud=FakeCloud(reachable=False))

        saved, synced, _ = service.create_reading(SERIAL, 120.0, None, None, API_KEY)

        self.assertEqual(len(repo.saved), 1)
        self.assertEqual(saved.level, "CAUTION")
        self.assertFalse(synced)

    def test_devuelve_la_orden_del_usuario_para_el_rele(self):
        service = build(cloud=FakeCloud(desired_plug="OFF"))

        _, _, desired = service.create_reading(SERIAL, 50.0, "ON", None, API_KEY)

        self.assertEqual(desired, "OFF")

    def test_un_campo_invalido_no_llega_a_persistirse(self):
        repo = FakeRepository()
        service = build(repository=repo)

        with self.assertRaises(ValueError):
            service.create_reading(SERIAL, "no-es-numero", None, None, API_KEY)

        self.assertEqual(repo.saved, [])


class ListReadingsTest(unittest.TestCase):
    def test_devuelve_las_lecturas_del_dispositivo_mas_recientes_primero(self):
        repo = FakeRepository()
        service = build(repository=repo)
        for valor in (10.0, 20.0, 30.0):
            service.create_reading(SERIAL, valor, None, None, API_KEY)

        rows = service.list_readings(SERIAL)

        self.assertEqual([r.field_ut for r in rows], [30.0, 20.0, 10.0])

    def test_filtra_por_serial(self):
        repo = FakeRepository()
        service = EmfMonitoringApplicationService(
            repository=repo,
            device_directory=FakeDirectory(),
            cloud=FakeCloud(),
        )
        service.create_reading(SERIAL, 10.0, None, None, API_KEY)

        self.assertEqual(len(service.list_readings(SERIAL)), 1)
        self.assertEqual(len(service.list_readings("OTRO")), 0)


if __name__ == "__main__":
    unittest.main()
