"""Tests de la regla de clasificacion: el edge es la autoridad de toda la plataforma.

Se usa `unittest` de la libreria estandar a proposito: el repo tiene cuatro
dependencias de produccion y ninguna de desarrollo, y se queda asi.

    python -m unittest discover -s tests -v
"""
import unittest

from monitoring.domain.value_objects import (
    CAUTION_UT,
    DANGER_UT,
    AlertLevel,
    MagneticField,
)


class MagneticFieldTest(unittest.TestCase):
    def test_acepta_un_numero(self):
        self.assertEqual(MagneticField.from_raw(45.2).micro_tesla, 45.2)

    def test_acepta_una_cadena_numerica(self):
        # El ESP32 manda JSON: el valor puede llegar como cadena.
        self.assertEqual(MagneticField.from_raw("45.2").micro_tesla, 45.2)

    def test_acepta_cero(self):
        self.assertEqual(MagneticField.from_raw(0).micro_tesla, 0.0)

    def test_rechaza_lo_que_no_es_numero(self):
        for malo in ("abc", None, [], {}):
            with self.subTest(valor=malo):
                with self.assertRaises(ValueError) as ctx:
                    MagneticField.from_raw(malo)
                # El endpoint devuelve este mensaje al dispositivo: no cambiarlo.
                self.assertEqual(str(ctx.exception), "field_uT invalido")

    def test_rechaza_negativos(self):
        with self.assertRaises(ValueError) as ctx:
            MagneticField.from_raw(-1)
        self.assertEqual(str(ctx.exception), "field_uT no puede ser negativo")

    def test_rechaza_nan(self):
        # NaN no es < 0 ni >= 0: sin comprobacion explicita se colaria.
        with self.assertRaises(ValueError):
            MagneticField.from_raw(float("nan"))

    def test_es_inmutable(self):
        field = MagneticField.from_raw(50)
        with self.assertRaises(Exception):
            field.micro_tesla = 999


class AlertLevelTest(unittest.TestCase):
    def nivel(self, micro_tesla):
        return AlertLevel.for_field(MagneticField.from_raw(micro_tesla))

    def test_por_debajo_del_umbral_de_precaucion_es_seguro(self):
        for valor in (0, 45.2, 99.99):
            with self.subTest(uT=valor):
                self.assertIs(self.nivel(valor), AlertLevel.SAFE)

    def test_el_umbral_de_precaucion_es_inclusivo(self):
        self.assertIs(self.nivel(100.0), AlertLevel.CAUTION)

    def test_entre_umbrales_es_precaucion(self):
        for valor in (100.01, 150.7, 199.99):
            with self.subTest(uT=valor):
                self.assertIs(self.nivel(valor), AlertLevel.CAUTION)

    def test_el_umbral_de_peligro_es_inclusivo(self):
        self.assertIs(self.nivel(200.0), AlertLevel.DANGER)

    def test_por_encima_del_umbral_de_peligro_es_peligro(self):
        for valor in (250.4, 10_000):
            with self.subTest(uT=valor):
                self.assertIs(self.nivel(valor), AlertLevel.DANGER)

    def test_los_umbrales_son_los_acordados_con_los_otros_stacks(self):
        # Duplicados en el backend (Java), la web (TS) y el movil (Dart).
        # Si estos cambian sin cambiar los otros, se rompe la coherencia.
        self.assertEqual(CAUTION_UT, 100.0)
        self.assertEqual(DANGER_UT, 200.0)

    def test_cada_nivel_arrastra_su_mensaje(self):
        for level in AlertLevel:
            with self.subTest(nivel=level.name):
                self.assertTrue(level.message)

    def test_los_mensajes_son_los_que_consumen_los_clientes(self):
        self.assertEqual(
            AlertLevel.SAFE.message,
            "Campo dentro de rango seguro. Equipo operando con normalidad.")
        self.assertEqual(
            AlertLevel.CAUTION.message,
            "Exposicion moderada. Se recomienda mantener distancia de la fuente.")
        self.assertEqual(
            AlertLevel.DANGER.message,
            "Nivel critico de EMF. Se recomienda cortar la energia del equipo.")

    def test_el_valor_que_viaja_por_la_api_es_en_mayusculas(self):
        # El backend persiste esta cadena tal cual y no reclasifica.
        self.assertEqual(AlertLevel.SAFE.wire_value, "SAFE")
        self.assertEqual(AlertLevel.CAUTION.wire_value, "CAUTION")
        self.assertEqual(AlertLevel.DANGER.wire_value, "DANGER")

    def test_solo_danger_aconseja_cortar(self):
        self.assertFalse(AlertLevel.SAFE.requires_cut_off)
        self.assertFalse(AlertLevel.CAUTION.requires_cut_off)
        self.assertTrue(AlertLevel.DANGER.requires_cut_off)


if __name__ == "__main__":
    unittest.main()
