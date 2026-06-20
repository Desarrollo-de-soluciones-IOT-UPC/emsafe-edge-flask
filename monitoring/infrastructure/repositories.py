"""Repositorio del Monitoring: persiste y reconstruye lecturas (SQLite local)."""
from monitoring.domain.entities import EmfReading
from monitoring.infrastructure.models import EmfReading as EmfReadingModel


class EmfReadingRepository:
    @staticmethod
    def save(reading: EmfReading) -> EmfReading:
        row = EmfReadingModel.create(
            serial_number=reading.serial_number,
            field_ut=reading.field_ut,
            level=reading.level,
            message=reading.message,
            plug=reading.plug,
            created_at=reading.created_at,
        )
        return EmfReading(
            reading.serial_number, reading.field_ut, reading.level,
            reading.message, reading.plug, reading.created_at, row.id,
        )

    @staticmethod
    def latest(serial_number=None, limit=50):
        q = EmfReadingModel.select().order_by(EmfReadingModel.id.desc())
        if serial_number:
            q = q.where(EmfReadingModel.serial_number == serial_number)
        q = q.limit(limit)
        return [
            EmfReading(r.serial_number, r.field_ut, r.level, r.message, r.plug, r.created_at, r.id)
            for r in q
        ]
