"""Value objects del Monitoring: el campo medido y su nivel de alerta.

El edge es la AUTORIDAD de la clasificacion: el backend confia en el `level`
que llega y no reclasifica. Por eso la regla vive aqui, en un tipo que no
puede existir con un valor invalido, y no suelta en un servicio.

Los umbrales estan duplicados a proposito en los otros tres stacks. Si cambias
estos, cambia los otros:
  - Back-End/.../radiationmonitoring/domain/services/RadiationLevel.java
  - Front-End/.../contexts/radiationmonitoring/domain/radiation-level.ts
  - Mobile_App (ver su contexto radiationmonitoring)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# Umbrales del sistema de alertas (uT). 200 uT ~ referencia ICNIRP (50 Hz, publico).
CAUTION_UT = 100.0
DANGER_UT = 200.0


@dataclass(frozen=True)
class MagneticField:
    """Magnitud de campo electromagnetico en microtesla.

    Todo viaja en uT de extremo a extremo (ESP32 -> edge -> backend -> clientes).
    Construirlo con un valor no numerico o negativo es imposible: la validacion
    que antes estaba en `EmfReadingService.create_reading` vive ahora en el tipo.
    """

    micro_tesla: float

    @classmethod
    def from_raw(cls, raw) -> "MagneticField":
        """Construye el VO desde el dato crudo del dispositivo.

        Raises:
            ValueError: si no es numerico o es negativo. Los mensajes se
                conservan literalmente porque el endpoint los devuelve al ESP32.
        """
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise ValueError("field_uT invalido")
        if value != value:  # NaN: float('nan') no es < 0 ni >= 0
            raise ValueError("field_uT invalido")
        if value < 0:
            raise ValueError("field_uT no puede ser negativo")
        return cls(value)

    def __float__(self) -> float:
        return self.micro_tesla


class AlertLevel(Enum):
    """Nivel de alerta, con su mensaje pegado.

    El nivel y el mensaje viajan siempre juntos. Antes `classify` los devolvia
    como una tupla suelta, de modo que nada impedia emparejar un nivel con el
    mensaje de otro; aqui la pareja es el propio valor del enum.
    """

    SAFE = ("SAFE", "Campo dentro de rango seguro. Equipo operando con normalidad.")
    CAUTION = ("CAUTION", "Exposicion moderada. Se recomienda mantener distancia de la fuente.")
    DANGER = ("DANGER", "Nivel critico de EMF. Se recomienda cortar la energia del equipo.")

    def __init__(self, wire_value: str, message: str) -> None:
        self._wire_value = wire_value
        self._message = message

    @property
    def wire_value(self) -> str:
        """Cadena que viaja por la API. El backend la persiste tal cual."""
        return self._wire_value

    @property
    def message(self) -> str:
        return self._message

    @classmethod
    def for_field(cls, field: MagneticField) -> "AlertLevel":
        """Clasifica el campo. Umbrales inclusivos por abajo: 100 uT ya es CAUTION."""
        value = field.micro_tesla
        if value < CAUTION_UT:
            return cls.SAFE
        if value < DANGER_UT:
            return cls.CAUTION
        return cls.DANGER

    @property
    def requires_cut_off(self) -> bool:
        """DANGER es el unico nivel en el que se recomienda cortar la energia."""
        return self is AlertLevel.DANGER
