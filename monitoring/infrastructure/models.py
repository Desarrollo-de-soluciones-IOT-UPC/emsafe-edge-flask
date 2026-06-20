"""Modelo ORM (Peewee) del Monitoring."""
from peewee import Model, AutoField, FloatField, CharField, DateTimeField

from shared.infrastructure.database import db


class EmfReading(Model):
    id = AutoField()
    serial_number = CharField()
    field_ut = FloatField()
    level = CharField()
    message = CharField()
    plug = CharField(null=True)
    created_at = DateTimeField()

    class Meta:
        database = db
        table_name = "emf_readings"
