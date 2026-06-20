"""Punto de entrada Flask del EMSafe Edge Service.

Registra los Blueprints de los bounded contexts IAM y Monitoring, e inicializa
la base de datos SQLite (crea tablas + siembra el dispositivo de prueba) una
sola vez antes de la primera request.

Uso:
    flask --app app run --host 0.0.0.0 --port 5000
    # o
    python app.py
"""
from flask import Flask, jsonify

import iam.application.services
from iam.interfaces.services import iam_api
from monitoring.interfaces.services import monitoring_api
from shared.infrastructure.database import init_db

app = Flask(__name__)
app.register_blueprint(iam_api)
app.register_blueprint(monitoring_api)

first_request = True


@app.before_request
def setup():
    """Inicializa la BD y siembra el dispositivo de prueba en la 1ra request."""
    global first_request
    if first_request:
        first_request = False
        init_db()
        iam.application.services.AuthApplicationService().get_or_create_test_device()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "UP", "service": "emsafe-edge"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
