"""Modelo ORM (Peewee) del IAM."""
from peewee import Model, CharField, DateTimeField

from shared.infrastructure.database import db


class Device(Model):
    device_id = CharField(primary_key=True)
    api_key = CharField()
    created_at = DateTimeField()

    class Meta:
        database = db
        table_name = "devices"
