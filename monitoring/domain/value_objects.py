"""Value Objects del bounded context Monitoring.

Espejan los del backend (`shared/domain/model/RadiationLevel.java`) a proposito: es
el mismo lenguaje ubicuo a los dos lados del cable.

EL EDGE ES LA AUTORIDAD DE LA ALERTA (E-4)
------------------------------------------
Los umbrales viven aqui y aqui se decide el nivel. El backend tiene los mismos
numeros en `RadiationLevel.CAUTION_UT/DANGER_UT`, pero NO reclasifica: respeta el
nivel que viene en la lectura y solo clasifica por valor cuando el dato llega sin
nivel (lecturas antiguas o de semilla). Si algun dia estos umbrales cambian, se
cambian AQUI; los del backend son solo la red de seguridad.

El firmware (`firmware/sketch.ino`) tiene su propia copia de los umbrales porque
necesita reaccionar sin red — LED y corte del rele — pero su decision es local e
inmediata, no la alerta oficial del sistema.
"""
from dataclasses import dataclass
from enum import Enum

# Umbrales del sistema de alertas (uT). 200 uT ~ referencia ICNIRP (50 Hz, publico).
CAUTION_UT = 100.0
DANGER_UT = 200.0


@dataclass(frozen=True)
class MagneticField:
    """Magnitud de campo magnetico, en microteslas.

    Antes era un `float` suelto y la validacion (convertir el dato crudo del ESP32 y
    rechazar negativos) estaba escrita dentro del servicio de dominio. Ahora un
    `MagneticField` no puede existir con un valor invalido.
    """

    value: float

    @staticmethod
    def from_raw(raw) -> "MagneticField":
        """Construye desde lo que mande el dispositivo (str o number)."""
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise ValueError("field_uT invalido")
        if value < 0:
            raise ValueError("field_uT no puede ser negativo")
        return MagneticField(value)

    def __float__(self):
        return self.value


class AlertLevel(Enum):
    """Nivel de alerta clasificado por el edge, con su mensaje.

    El mensaje va pegado al nivel porque es una funcion de el: antes se devolvian
    como una tupla `(nivel, mensaje)` y cada consumidor tenia que acordarse de
    llevarlos juntos.
    """

    SAFE = ("SAFE", "Campo dentro de rango seguro. Equipo operando con normalidad.")
    CAUTION = ("CAUTION", "Exposicion moderada. Se recomienda mantener distancia de la fuente.")
    DANGER = ("DANGER", "Nivel critico de EMF. Se recomienda cortar la energia del equipo.")

    def __init__(self, wire_value: str, message: str):
        self.wire_value = wire_value
        self.message = message

    @staticmethod
    def for_field(field: MagneticField) -> "AlertLevel":
        """La clasificacion del sistema de alertas: la unica puerta para decidir nivel."""
        if field.value < CAUTION_UT:
            return AlertLevel.SAFE
        if field.value < DANGER_UT:
            return AlertLevel.CAUTION
        return AlertLevel.DANGER

    @staticmethod
    def from_persisted(value) -> "AlertLevel":
        """Lectura tolerante desde SQLite: un valor desconocido se toma como SAFE."""
        if value:
            for level in AlertLevel:
                if level.wire_value == str(value).strip().upper():
                    return level
        return AlertLevel.SAFE

    def is_dangerous(self) -> bool:
        return self is AlertLevel.DANGER
