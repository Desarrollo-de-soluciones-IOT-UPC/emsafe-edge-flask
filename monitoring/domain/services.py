"""Servicios de dominio del Monitoring: el SISTEMA DE ALERTAS.

Aqui vive la logica que el profesor pide que corra en el edge: el edge recibe
el valor crudo del campo y EL MISMO clasifica el nivel de alerta
(Safe / Caution / Danger) y genera el mensaje. El dispositivo conserva su
reaccion local inmediata (LED + corte), pero el edge es la autoridad de la alerta.
"""
from datetime import datetime, timezone

from dateutil.parser import parse

from monitoring.domain.entities import EmfReading

# Umbrales del sistema de alertas (uT). 200 uT ~ referencia ICNIRP (50 Hz, publico).
UMBRAL_CAUTION_UT = 100.0
UMBRAL_DANGER_UT = 200.0


class EmfReadingService:
    @staticmethod
    def classify(field_ut: float):
        """Clasifica el campo en SAFE / CAUTION / DANGER y devuelve (nivel, mensaje)."""
        if field_ut < UMBRAL_CAUTION_UT:
            return "SAFE", "Campo dentro de rango seguro. Equipo operando con normalidad."
        elif field_ut < UMBRAL_DANGER_UT:
            return "CAUTION", "Exposicion moderada. Se recomienda mantener distancia de la fuente."
        else:
            return "DANGER", "Nivel critico de EMF. Se recomienda cortar la energia del equipo."

    @staticmethod
    def create_reading(serial_number, field_ut, plug, created_at) -> EmfReading:
        """Valida el dato crudo, clasifica el nivel y construye la entidad."""
        try:
            field_ut = float(field_ut)
        except (TypeError, ValueError):
            raise ValueError("field_uT invalido")
        if field_ut < 0:
            raise ValueError("field_uT no puede ser negativo")

        parsed = EmfReadingService._parse_time(created_at)
        level, message = EmfReadingService.classify(field_ut)
        return EmfReading(serial_number, field_ut, level, message, plug, parsed)

    @staticmethod
    def _parse_time(created_at):
        if not created_at:
            return datetime.now(timezone.utc)
        try:
            # El ESP32 envia 'dd/mm/YYYY HH:MM:SS' -> dayfirst=True
            return parse(created_at, dayfirst=True).astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError):
            return datetime.now(timezone.utc)
