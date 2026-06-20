"""Capa de interfaz (REST) del IAM + helper de autenticacion reutilizable."""
from flask import Blueprint, request, jsonify

from iam.application.services import AuthApplicationService

iam_api = Blueprint("iam_api", __name__)
auth_service = AuthApplicationService()


def authenticate_request():
    """Valida la identidad del dispositivo (device_id en el body + X-API-Key).

    Devuelve una tupla (respuesta, 401) si la auth falla, o None si es valida.
    Acepta 'device_id', 'deviceId' o 'serialNumber' en el body para ser flexible
    con el formato que envia el ESP32.
    """
    body = request.json if request.is_json else None
    device_id = None
    if body:
        device_id = body.get("device_id") or body.get("deviceId") or body.get("serialNumber")
    api_key = request.headers.get("X-API-Key")
    if not device_id or not api_key:
        return jsonify({"error": "Missing device_id or X-API-Key"}), 401
    if not auth_service.authenticate(device_id, api_key):
        return jsonify({"error": "Invalid device_id or API key"}), 401
    return None
