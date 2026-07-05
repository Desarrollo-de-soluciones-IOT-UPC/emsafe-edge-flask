"""Sincronizacion con el backend en la nube (Azure).

Tras procesar y persistir localmente, el edge reenvia la lectura al backend
real usando el endpoint de ingesta que ya existe: POST /api/v1/readings.
Se autentica con JWT (POST /api/auth/login).

Por defecto el sync esta DESACTIVADO para que el edge corra sin depender de
la nube. Ponlo en True (o via variables de entorno) cuando quieras sincronizar.
"""
import os

import requests

CLOUD = {
    "enabled": os.getenv("EMSAFE_SYNC_ENABLED", "false").lower() == "true",
    "base_url": os.getenv(
        "EMSAFE_BACKEND_URL",
        "https://emsafe-backend-hmf7asgja0d0h4cr.centralus-01.azurewebsites.net",
    ),
    "login_path": "/api/auth/login",
    "ingest_path": "/api/v1/readings",
    # Recomendado: mover a variables de entorno, no dejarlo en el repo.
    "email": os.getenv("EMSAFE_BACKEND_EMAIL", "admin@emsafe.com"),
    "password": os.getenv("EMSAFE_BACKEND_PASSWORD", "admin123"),
}


class CloudSyncService:
    def __init__(self):
        self._token = None

    def _login(self):
        url = CLOUD["base_url"] + CLOUD["login_path"]
        resp = requests.post(
            url, json={"email": CLOUD["email"], "password": CLOUD["password"]}, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        # Respuesta envuelta: ApiResponse -> data -> token
        self._token = (data.get("data") or {}).get("token")
        return self._token

    def sync_reading(self, serial_number, level, message, field_ut, plug=None) -> bool:
        """Reenvia la lectura al backend (incluye el estado del rele). True si se sincronizo."""
        if not CLOUD["enabled"]:
            return False
        payload = {
            "serialNumber": serial_number,
            "level": level,
            "message": message,
            "field_uT": field_ut,
            "plug": plug,
        }
        url = CLOUD["base_url"] + CLOUD["ingest_path"]
        try:
            if not self._token:
                self._login()
            resp = requests.post(
                url, json=payload, headers={"Authorization": f"Bearer {self._token}"}, timeout=10
            )
            if resp.status_code == 401:        # token vencido -> re-login y reintenta
                self._login()
                resp = requests.post(
                    url, json=payload, headers={"Authorization": f"Bearer {self._token}"}, timeout=10
                )
            return 200 <= resp.status_code < 300
        except Exception as e:
            # Resiliencia: si la nube falla, el edge sigue (dato ya guardado local)
            print(f"[EDGE][SYNC] fallo al sincronizar con la nube: {e}")
            return False

    def fetch_desired_plug(self, serial_number):
        """Consulta al backend el estado DESEADO del rele (orden del usuario desde
        la app: ON/OFF). Camino de vuelta mobile -> backend -> edge -> dispositivo.
        Endpoint publico (sin JWT). Devuelve "ON" | "OFF" | None."""
        if not CLOUD["enabled"]:
            return None
        url = f"{CLOUD['base_url']}/api/v1/devices/{serial_number}/plug"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return None
            data = resp.json()
            # Respuesta envuelta: ApiResponse -> data -> desiredPlug
            return (data.get("data") or {}).get("desiredPlug")
        except Exception as e:
            print(f"[EDGE][SYNC] fallo al consultar desired plug: {e}")
            return None
