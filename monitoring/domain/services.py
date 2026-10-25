"""Servicios de dominio del Monitoring: el SISTEMA DE ALERTAS.

Aqui vive la logica que el profesor pide que corra en el edge: el edge recibe
el valor crudo del campo y EL MISMO clasifica el nivel de alerta
(Safe / Caution / Danger) y genera el mensaje. El dispositivo conserva su
reaccion local inmediata (LED + corte), pero el edge es la autoridad de la alerta.

La regla de clasificacion y los umbrales viven en `value_objects`: aqui solo
queda la orquestacion de construir una lectura valida.
"""
from datetime import datetime, timezone

from dateutil.parser import parse

from monitoring.domain.entities import EmfReading
from monitoring.domain.value_objects import AlertLevel, MagneticField

# Se reexportan para no romper a quien los importara desde aqui.
from monitoring.domain.value_objects import (  # noqa: F401
    CAUTION_UT as UMBRAL_CAUTION_UT,
    DANGER_UT as UMBRAL_DANGER_UT,
)


class EmfReadingService:
    @staticmethod
    def classify(field_ut) -> AlertLevel:
        """Clasifica el campo crudo y devuelve el nivel (que ya lleva su mensaje).

        Antes devolvia la tupla `(nivel, mensaje)`; ahora devuelve un
        `AlertLevel`, que mantiene ambos unidos. Usa `.wire_value` y `.message`
        para obtener las cadenas que viajan por la API.
        """
        return AlertLevel.for_field(MagneticField.from_raw(field_ut))

    @staticmethod
    def create_reading(serial_number, field_ut, plug, created_at) -> EmfReading:
        """Valida el dato crudo, clasifica el nivel y construye la entidad."""
        field = MagneticField.from_raw(field_ut)
        level = AlertLevel.for_field(field)
        parsed = EmfReadingService._parse_time(created_at)
        return EmfReading(
            serial_number, field.micro_tesla, level.wire_value, level.message, plug, parsed
        )

    @staticmethod
    def _parse_time(created_at):
        if not created_at:
            return datetime.now(timezone.utc)
        try:
            # El ESP32 envia 'dd/mm/YYYY HH:MM:SS' -> dayfirst=True
            return parse(created_at, dayfirst=True).astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError):
            return datetime.now(timezone.utc)
