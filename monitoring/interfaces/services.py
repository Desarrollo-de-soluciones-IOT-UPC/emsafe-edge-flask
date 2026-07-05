"""Capa de interfaz (REST) del Monitoring."""
from flask import Blueprint, request, jsonify

from iam.interfaces.services import authenticate_request
from monitoring.application.services import EmfMonitoringApplicationService

monitoring_api = Blueprint("monitoring_api", __name__)
service = EmfMonitoringApplicationService()


@monitoring_api.route("/api/v1/emf-monitoring/data-records", methods=["POST"])
def create_emf_reading():
    """Ingesta de una lectura EMF enviada por el dispositivo (ESP32).

    Headers:
        X-API-Key: clave del dispositivo.
    Body (JSON):
        { "device_id": "EMSAFE-6766-01", "field_uT": 250.4, "plug": "OFF",
          "created_at": "19/06/2026 18:40:12" }
    El edge clasifica el nivel (SAFE/CAUTION/DANGER), persiste local y sincroniza.
    """
    auth_result = authenticate_request()
    if auth_result:
        return auth_result

    data = request.json or {}
    serial = data.get("device_id") or data.get("deviceId") or data.get("serialNumber")
    field_ut = data.get("field_uT", data.get("field_ut"))
    plug = data.get("plug")
    created_at = data.get("created_at") or data.get("time")

    if serial is None or field_ut is None:
        return jsonify({"error": "Missing device_id or field_uT"}), 400

    try:
        saved, synced, desired_plug = service.create_reading(
            serial, field_ut, plug, created_at, request.headers.get("X-API-Key")
        )
        # desiredPlug viaja en la respuesta: el dispositivo puede leerla en el
        # mismo ciclo POST y accionar el rele (orden del usuario desde la app).
        return jsonify({
            "id": saved.id,
            "serialNumber": saved.serial_number,
            "field_uT": saved.field_ut,
            "level": saved.level,
            "message": saved.message,
            "plug": saved.plug,
            "desiredPlug": desired_plug,
            "syncedToCloud": synced,
            "created_at": saved.created_at.isoformat(),
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@monitoring_api.route("/api/v1/emf-monitoring/readings", methods=["GET"])
def list_emf_readings():
    """Lista las lecturas guardadas localmente (para inspeccion / demo)."""
    serial = request.args.get("serialNumber")
    limit = int(request.args.get("limit", 50))
    readings = service.list_readings(serial, limit)
    return jsonify([
        {
            "id": r.id, "serialNumber": r.serial_number, "field_uT": r.field_ut,
            "level": r.level, "message": r.message, "plug": r.plug,
            "created_at": r.created_at.isoformat() if hasattr(r.created_at, "isoformat") else str(r.created_at),
        }
        for r in readings
    ])
