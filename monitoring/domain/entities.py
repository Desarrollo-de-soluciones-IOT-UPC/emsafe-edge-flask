"""Entidades de dominio del bounded context Monitoring."""
from monitoring.domain.value_objects import AlertLevel, MagneticField


class EmfReading:
    """Aggregate root: una lectura de campo electromagnetico.

    La identidad NO se pasa al construir (E-2): una lectura recien clasificada
    todavia no existe para la persistencia, y el `id` era un parametro opcional que
    dejaba colar un detalle de infraestructura dentro del dominio. Ahora nace sin id
    y el repositorio se lo asigna al guardarla con `assign_identity`, o la reconstruye
    entera con `restore` al leerla de SQLite.

    Attributes:
        id (int | None): Identidad, asignada por la persistencia.
        serial_number (str): Numero de serie del dispositivo.
        field (MagneticField): Magnitud del campo.
        level (AlertLevel): Nivel de alerta clasificado por el edge.
        plug (str | None): Estado del enchufe inteligente (ON / OFF).
        created_at (datetime): Marca de tiempo de la lectura (UTC).
    """

    def __init__(self, serial_number, field: MagneticField, level: AlertLevel, plug, created_at):
        self.id = None
        self.serial_number = serial_number
        self.field = field
        self.level = level
        self.plug = plug
        self.created_at = created_at

    @classmethod
    def restore(cls, id, serial_number, field_ut, level, plug, created_at) -> "EmfReading":
        """Reconstruye una lectura ya guardada. Uso exclusivo del repositorio."""
        reading = cls(
            serial_number,
            MagneticField(float(field_ut)),
            AlertLevel.from_persisted(level),
            plug,
            created_at,
        )
        reading.id = id
        return reading

    def assign_identity(self, id) -> "EmfReading":
        """La persistencia le da su identidad. Solo puede ocurrir una vez."""
        if self.id is not None:
            raise ValueError("La lectura ya tiene identidad asignada")
        self.id = id
        return self

    # ─── Proyecciones para la API y la persistencia ──────────────────────────
    # Mantienen intacto el JSON de siempre aunque por dentro haya VOs.

    @property
    def field_ut(self) -> float:
        return self.field.value

    @property
    def level_name(self) -> str:
        return self.level.wire_value

    @property
    def message(self) -> str:
        """Deriva del nivel: dejo de ser un campo suelto que podia quedar incoherente."""
        return self.level.message

    def is_dangerous(self) -> bool:
        return self.level.is_dangerous()
