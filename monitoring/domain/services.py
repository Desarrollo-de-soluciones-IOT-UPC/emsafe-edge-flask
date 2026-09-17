"""Servicios de dominio del Monitoring: el SISTEMA DE ALERTAS.

Aqui vive la logica que el profesor pide que corra en el edge: el edge recibe
el valor crudo del campo y EL MISMO clasifica el nivel de alerta
(Safe / Caution / Danger) y genera el mensaje. El dispositivo conserva su
reaccion local inmediata (LED + corte), pero el edge es la autoridad de la alerta.

Los umbrales y la clasificacion se mudaron a `monitoring/domain/value_objects.py`
(E-1/E-4): la regla es del VO `AlertLevel`, no de este servicio. Lo que queda aqui
es lo unico que sigue siendo orquestacion de dominio: convertir el dato crudo del
dispositivo en una lectura valida.
"""
from datetime import datetime, timezone

from dateutil.parser import parse

from monitoring.domain.entities import EmfReading
from monitoring.domain.value_objects import AlertLevel, MagneticField


class EmfReadingService:
    @staticmethod
    def create_reading(serial_number, field_ut, plug, created_at) -> EmfReading:
        """Valida el dato crudo, clasifica el nivel y construye la entidad."""
        field = MagneticField.from_raw(field_ut)
        level = AlertLevel.for_field(field)
        parsed = EmfReadingService._parse_time(created_at)
        return EmfReading(serial_number, field, level, plug, parsed)

    @staticmethod
    def _parse_time(created_at):
        if not created_at:
            return datetime.now(timezone.utc)
        try:
            # El ESP32 envia 'dd/mm/YYYY HH:MM:SS' -> dayfirst=True
            return parse(created_at, dayfirst=True).astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError):
            return datetime.now(timezone.utc)
