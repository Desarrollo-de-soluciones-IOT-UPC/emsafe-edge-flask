"""Integracion de la ingesta a traves de HTTP: el contrato del ESP32.

Recorre la pila completa (blueprint -> interfaz -> aplicacion -> dominio ->
SQLite) con el cliente de test de Flask, sin abrir ningun puerto.

La sincronizacion con la nube se deja explicitamente apagada para que la suite
no haga peticiones de red. Es el valor por defecto, pero se fija aqui por si
alguien exporta `EMSAFE_SYNC_ENABLED` en su shell.
"""
import os
import unittest

os.environ.setdefault("EMSAFE_SYNC_ENABLED", "false")

import app as edge_app  # noqa: E402  (tras fijar el entorno)
from iam.infrastructure.repositories import TEST_API_KEY, TEST_DEVICE_ID  # noqa: E402

RUTA_INGESTA = "/api/v1/emf-monitoring/data-records"
RUTA_ALIAS_FIRMWARE = "/api/v1/data_records"
RUTA_LECTURAS = "/api/v1/emf-monitoring/readings"


class IngestEndpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        edge_app.app.config.update(TESTING=True)
        cls.client = edge_app.app.test_client()

    def post(self, body, api_key=TEST_API_KEY, ruta=RUTA_INGESTA):
        return self.client.post(ruta, json=body, headers={"X-API-Key": api_key})

    def test_una_lectura_segura_se_clasifica_y_persiste(self):
        resp = self.post({"device_id": TEST_DEVICE_ID, "field_uT": 45.2, "plug": "ON"})

        self.assertEqual(resp.status_code, 201)
        cuerpo = resp.get_json()
        self.assertEqual(cuerpo["level"], "SAFE")
        self.assertEqual(cuerpo["field_uT"], 45.2)
        self.assertEqual(cuerpo["plug"], "ON")
        self.assertIsNotNone(cuerpo["id"])            # SQLite le dio identidad
        self.assertIn("Campo dentro de rango seguro", cuerpo["message"])

    def test_los_tres_niveles_salen_por_la_api(self):
        casos = [(45.2, "SAFE"), (150.7, "CAUTION"), (275.0, "DANGER")]
        for micro_tesla, esperado in casos:
            with self.subTest(uT=micro_tesla):
                resp = self.post({"device_id": TEST_DEVICE_ID, "field_uT": micro_tesla})
                self.assertEqual(resp.status_code, 201)
                self.assertEqual(resp.get_json()["level"], esperado)

    def test_las_fronteras_exactas_tambien_por_la_api(self):
        for micro_tesla, esperado in [(100.0, "CAUTION"), (200.0, "DANGER")]:
            with self.subTest(uT=micro_tesla):
                resp = self.post({"device_id": TEST_DEVICE_ID, "field_uT": micro_tesla})
                self.assertEqual(resp.get_json()["level"], esperado)

    def test_el_alias_del_firmware_congelado_sigue_funcionando(self):
        # El sketch flasheado postea a /api/v1/data_records (guion bajo).
        # Romperlo obligaria a re-flashear el ESP32.
        resp = self.post(
            {"device_id": TEST_DEVICE_ID, "field_uT": 10.0}, ruta=RUTA_ALIAS_FIRMWARE)

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["level"], "SAFE")

    def test_acepta_la_fecha_en_el_formato_del_dispositivo(self):
        resp = self.post({
            "device_id": TEST_DEVICE_ID, "field_uT": 10.0,
            "created_at": "19/06/2026 18:40:12",
        })

        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.get_json()["created_at"].startswith("2026-06-19"))

    def test_acepta_los_alias_de_nombre_de_campo(self):
        # El firmware ha usado varias grafias a lo largo del proyecto.
        for clave_serial in ("device_id", "deviceId", "serialNumber"):
            with self.subTest(clave=clave_serial):
                resp = self.post({clave_serial: TEST_DEVICE_ID, "field_uT": 10.0})
                self.assertEqual(resp.status_code, 201)

    def test_una_api_key_incorrecta_devuelve_401(self):
        resp = self.post({"device_id": TEST_DEVICE_ID, "field_uT": 10.0}, api_key="clave-mala")

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["error"], "Invalid device_id or API key")

    def test_sin_el_header_devuelve_401_con_otro_motivo(self):
        # Mensaje distinto al de clave incorrecta: el firmware los distingue.
        resp = self.client.post(RUTA_INGESTA, json={"device_id": TEST_DEVICE_ID, "field_uT": 10.0})

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["error"], "Missing device_id or X-API-Key")

    def test_un_serial_desconocido_no_ingesta(self):
        resp = self.post({"device_id": "SERIAL-QUE-NO-EXISTE", "field_uT": 10.0})

        self.assertEqual(resp.status_code, 401)

    def test_un_campo_invalido_devuelve_400_con_el_motivo(self):
        resp = self.post({"device_id": TEST_DEVICE_ID, "field_uT": "no-es-numero"})

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"], "field_uT invalido")

    def test_un_campo_negativo_devuelve_400(self):
        resp = self.post({"device_id": TEST_DEVICE_ID, "field_uT": -5})

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"], "field_uT no puede ser negativo")

    def test_faltando_el_campo_devuelve_400(self):
        resp = self.post({"device_id": TEST_DEVICE_ID})

        self.assertEqual(resp.status_code, 400)
        self.assertIn("Missing", resp.get_json()["error"])

    def test_la_respuesta_lleva_la_orden_para_el_rele(self):
        # desiredPlug viaja en el POST para que el dispositivo accione el rele
        # en el mismo ciclo. Sin nube alcanzable viene a None, pero la clave
        # debe estar siempre: el firmware la lee.
        resp = self.post({"device_id": TEST_DEVICE_ID, "field_uT": 10.0, "plug": "ON"})

        self.assertIn("desiredPlug", resp.get_json())
        self.assertIn("syncedToCloud", resp.get_json())


class ListReadingsEndpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        edge_app.app.config.update(TESTING=True)
        cls.client = edge_app.app.test_client()

    def test_las_lecturas_ingeridas_se_pueden_recuperar(self):
        self.client.post(
            RUTA_INGESTA,
            json={"device_id": TEST_DEVICE_ID, "field_uT": 199.9},
            headers={"X-API-Key": TEST_API_KEY},
        )

        resp = self.client.get(f"{RUTA_LECTURAS}?serialNumber={TEST_DEVICE_ID}&limit=5")

        self.assertEqual(resp.status_code, 200)
        filas = resp.get_json()
        self.assertGreater(len(filas), 0)
        # La ultima ingerida sale primero y conserva nivel y mensaje emparejados.
        self.assertEqual(filas[0]["field_uT"], 199.9)
        self.assertEqual(filas[0]["level"], "CAUTION")

    def test_un_serial_desconocido_devuelve_lista_vacia(self):
        resp = self.client.get(f"{RUTA_LECTURAS}?serialNumber=NO-EXISTE-ESTE-SERIAL")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), [])


if __name__ == "__main__":
    unittest.main()
