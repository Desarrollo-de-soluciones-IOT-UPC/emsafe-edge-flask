"""Entidades de dominio del bounded context Monitoring."""
from datetime import datetime


class EmfReading:
    """Aggregate root: una lectura de campo electromagnetico.

    Attributes:
        id (int | None): Identidad asignada por la persistencia.
        serial_number (str): Numero de serie del dispositivo.
        field_ut (float): Magnitud del campo en microteslas.
        level (str): Nivel de alerta clasificado (SAFE / CAUTION / DANGER).
        message (str): Mensaje contextual segun el nivel.
        plug (str | None): Estado del enchufe inteligente (ON / OFF).
        created_at (datetime): Marca de tiempo de la lectura (UTC).
    """

    def __init__(self, serial_number, field_ut, level, message, plug, created_at, id=None):
        self.id = id
        self.serial_number = serial_number
        self.field_ut = field_ut
        self.level = level
        self.message = message
        self.plug = plug
        self.created_at = created_at
