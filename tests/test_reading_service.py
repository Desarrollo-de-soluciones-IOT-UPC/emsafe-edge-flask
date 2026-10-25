"""Tests del servicio de dominio que construye la lectura."""
import unittest
from datetime import datetime, timezone

from monitoring.domain.services import EmfReadingService
from monitoring.domain.value_objects import AlertLevel


class CreateReadingTest(unittest.TestCase):
    def test_clasifica_y_empareja_nivel_con_mensaje(self):
        reading = EmfReadingService.create_reading("EMSAFE-6766-01", 275.0, "ON", None)

        self.assertEqual(reading.level, "DANGER")
        self.assertEqual(reading.message, AlertLevel.DANGER.message)

    def test_guarda_el_campo_como_float(self):
        # Llega como cadena desde el JSON del ESP32 y debe persistirse numerico.
        reading = EmfReadingService.create_reading("EMSAFE-6766-01", "45.2", None, None)

        self.assertIsInstance(reading.field_ut, float)
        self.assertEqual(reading.field_ut, 45.2)

    def test_propaga_el_serial_y_el_estado_del_rele(self):
        reading = EmfReadingService.create_reading("EMSAFE-6766-01", 10, "OFF", None)

        self.assertEqual(reading.serial_number, "EMSAFE-6766-01")
        self.assertEqual(reading.plug, "OFF")

    def test_rechaza_un_campo_invalido(self):
        with self.assertRaises(ValueError):
            EmfReadingService.create_reading("EMSAFE-6766-01", "no-es-un-numero", None, None)

    def test_rechaza_un_campo_negativo(self):
        with self.assertRaises(ValueError):
            EmfReadingService.create_reading("EMSAFE-6766-01", -5, None, None)

    def test_la_lectura_nueva_no_tiene_identidad_hasta_persistirse(self):
        reading = EmfReadingService.create_reading("EMSAFE-6766-01", 10, None, None)
        self.assertIsNone(reading.id)


class TimeParsingTest(unittest.TestCase):
    def test_interpreta_el_formato_del_esp32_con_el_dia_primero(self):
        # 'dd/mm/YYYY': el 06/07 es 6 de julio, no 7 de junio.
        reading = EmfReadingService.create_reading(
            "EMSAFE-6766-01", 10, None, "06/07/2026 14:30:00")

        self.assertEqual(reading.created_at.day, 6)
        self.assertEqual(reading.created_at.month, 7)
        self.assertEqual(reading.created_at.year, 2026)

    def test_sin_fecha_usa_la_hora_actual_en_utc(self):
        reading = EmfReadingService.create_reading("EMSAFE-6766-01", 10, None, None)

        self.assertEqual(reading.created_at.tzinfo, timezone.utc)
        delta = abs((datetime.now(timezone.utc) - reading.created_at).total_seconds())
        self.assertLess(delta, 60)

    def test_una_fecha_corrupta_no_tumba_la_ingesta(self):
        # Perder la marca de tiempo no debe costar la lectura entera.
        reading = EmfReadingService.create_reading(
            "EMSAFE-6766-01", 10, None, "fecha-que-no-se-puede-parsear")

        self.assertIsNotNone(reading.created_at)
        self.assertEqual(reading.created_at.tzinfo, timezone.utc)


class ReadingBehaviourTest(unittest.TestCase):
    def test_reconoce_cuando_hay_que_cortar_la_energia(self):
        peligrosa = EmfReadingService.create_reading("S", 275.0, None, None)
        normal = EmfReadingService.create_reading("S", 50.0, None, None)

        self.assertTrue(peligrosa.is_dangerous())
        self.assertFalse(normal.is_dangerous())

    def test_recupera_los_value_objects(self):
        reading = EmfReadingService.create_reading("S", 150.0, None, None)

        self.assertEqual(reading.field().micro_tesla, 150.0)
        self.assertIs(reading.alert_level(), AlertLevel.CAUTION)

    def test_sabe_de_que_dispositivo_es(self):
        reading = EmfReadingService.create_reading("EMSAFE-6766-01", 10, None, None)

        self.assertTrue(reading.belongs_to("EMSAFE-6766-01"))
        self.assertFalse(reading.belongs_to("OTRO-SERIAL"))


if __name__ == "__main__":
    unittest.main()
