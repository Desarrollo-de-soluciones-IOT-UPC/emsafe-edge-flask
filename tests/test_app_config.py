"""Comprobaciones de configuracion del arranque.

El modo debug se verifica por comportamiento y no solo buscando `debug=True`
en el texto del archivo: un grep se equivoca en los dos sentidos (lo encuentra
en un comentario que lo menciona, y no lo ve si alguien lo asigna en otra linea).
"""
import os
import unittest

import app as edge_app


class DebugFlagTest(unittest.TestCase):
    def setUp(self):
        self._previo = os.environ.get("EMSAFE_EDGE_DEBUG")

    def tearDown(self):
        if self._previo is None:
            os.environ.pop("EMSAFE_EDGE_DEBUG", None)
        else:
            os.environ["EMSAFE_EDGE_DEBUG"] = self._previo

    def test_apagado_por_defecto(self):
        # Werkzeug en debug expone una consola con ejecucion de codigo
        # arbitraria, y el edge escucha en 0.0.0.0.
        os.environ.pop("EMSAFE_EDGE_DEBUG", None)
        self.assertFalse(edge_app._debug_enabled())

    def test_se_puede_activar_a_mano(self):
        for valor in ("1", "true", "TRUE", "yes", " true "):
            with self.subTest(valor=valor):
                os.environ["EMSAFE_EDGE_DEBUG"] = valor
                self.assertTrue(edge_app._debug_enabled())

    def test_cualquier_otro_valor_lo_deja_apagado(self):
        for valor in ("0", "false", "no", "", "quizas"):
            with self.subTest(valor=valor):
                os.environ["EMSAFE_EDGE_DEBUG"] = valor
                self.assertFalse(edge_app._debug_enabled())


class HealthEndpointTest(unittest.TestCase):
    def test_responde_up(self):
        # Cliente de test de Flask: no levanta el servidor, pero SI dispara el
        # `before_request`, asi que `init_db()` corre y crea `emsafe_edge.db`
        # en el directorio del repo. Esta en .gitignore (`*.db`), por lo que no
        # ensucia el arbol; conviene saberlo antes de extranarse del fichero.
        edge_app.app.config.update(TESTING=True)
        with edge_app.app.test_client() as client:
            resp = client.get("/health")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "UP")
        self.assertEqual(resp.get_json()["service"], "emsafe-edge")


if __name__ == "__main__":
    unittest.main()
