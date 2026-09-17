"""Repositorio del Monitoring: persiste y reconstruye lecturas (SQLite local)."""
from monitoring.domain.entities import EmfReading
from monitoring.infrastructure.models import EmfReading as EmfReadingModel


class EmfReadingRepository:
    @staticmethod
    def save(reading: EmfReading) -> EmfReading:
        """Guarda la lectura y le devuelve su identidad (E-2)."""
        row = EmfReadingModel.create(
            serial_number=reading.serial_number,
            field_ut=reading.field_ut,
            level=reading.level_name,
            message=reading.message,
            plug=reading.plug,
            created_at=reading.created_at,
        )
        return reading.assign_identity(row.id)

    @staticmethod
    def latest(serial_number=None, limit=50):
        q = EmfReadingModel.select().order_by(EmfReadingModel.id.desc())
        if serial_number:
            q = q.where(EmfReadingModel.serial_number == serial_number)
        q = q.limit(limit)
        return [
            EmfReading.restore(r.id, r.serial_number, r.field_ut, r.level, r.plug, r.created_at)
            for r in q
        ]
