"""Infraestructura de base de datos compartida (SQLite via Peewee)."""
from peewee import SqliteDatabase

db = SqliteDatabase("emsafe_edge.db")


def init_db() -> None:
    """Abre la conexion y crea las tablas si no existen (idempotente)."""
    db.connect(reuse_if_open=True)
    from iam.infrastructure.models import Device
    from monitoring.infrastructure.models import EmfReading
    db.create_tables([Device, EmfReading], safe=True)
    db.close()
