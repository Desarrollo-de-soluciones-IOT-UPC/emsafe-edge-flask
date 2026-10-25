"""Entidades de dominio del bounded context Monitoring."""
from datetime import datetime

from monitoring.domain.value_objects import AlertLevel, MagneticField


class EmfReading:
    """Aggregate root: una lectura de campo electromagnetico.

    Guarda primitivas a proposito: el repositorio las escribe directamente en
    SQLite y `CloudSyncService` las manda al backend sin transformar. Los value
    objects (`MagneticField`, `AlertLevel`) se usan al construirla y se pueden
    recuperar con `field()` y `alert_level()`.

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

    # ─── Comportamiento del agregado ────────────────────────────────────────

    def field(self) -> MagneticField:
        """El campo medido como value object."""
        return MagneticField(self.field_ut)

    def alert_level(self) -> AlertLevel:
        """El nivel clasificado como value object."""
        return AlertLevel[self.level]

    def is_dangerous(self) -> bool:
        """True si el nivel aconseja cortar la energia del equipo."""
        return self.alert_level().requires_cut_off

    def belongs_to(self, serial_number: str) -> bool:
        return self.serial_number == serial_number

    def __repr__(self) -> str:
        return (f"EmfReading({self.serial_number}, {self.field_ut} uT, "
                f"{self.level}, plug={self.plug})")
