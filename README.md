# EMSafe Edge Service (Flask + DDD)

Capa **edge** local de EMSafe, en Flask con arquitectura **DDD** (bounded contexts),
siguiendo el patrón del ejemplo `smart-band-edge-service`.

```
ESP32  -->  EDGE (Flask, local)  -->  Backend Azure  -->  Web/App
            clasifica Safe/Caution/Danger,
            guarda local (SQLite) y sincroniza
```

## Bounded contexts
- **iam/** — autentica al dispositivo por API key (`X-API-Key`).
- **monitoring/** — recibe el `field_uT`, **clasifica el nivel de alerta (SAFE/CAUTION/DANGER)**
  en el domain service, persiste en SQLite y **sincroniza** al backend de Azure.
- **shared/** — base de datos SQLite compartida (Peewee).

## Requisitos
- Python 3.10+

## Correr en IntelliJ / PyCharm o terminal
```bash
# 1. crear entorno virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 2. instalar dependencias
pip install -r requirements.txt

# 3. correr
python app.py
```
Arranca en `http://localhost:5000`.

> En IntelliJ: abre la carpeta, configura un intérprete de Python (con el venv),
> y dale Run a `app.py`.

### Modo debug

El debug de Flask está **apagado por defecto** y se activa por entorno:

```bash
EMSAFE_EDGE_DEBUG=true python app.py
```

Antes estaba fijo a `debug=True` en el código. Combinado con `host=0.0.0.0`,
eso dejaba el debugger de Werkzeug —que permite ejecutar código arbitrario—
accesible a toda la red local, la misma en la que está el prototipo (y expuesto
a internet cuando se usa el túnel de ngrok para Wokwi).

## Tests

```bash
python -m unittest discover -s tests -v     # -b para silenciar los print del edge
```

Sin dependencias de desarrollo: `unittest` viene en la librería estándar y el
repo se queda con sus cuatro dependencias de producción.

Qué cubren:

| Archivo | Qué fija |
|---|---|
| `test_value_objects.py` | La clasificación y los umbrales 100/200 µT, incluidas las fronteras exactas, y que `MagneticField` rechace lo inválido |
| `test_reading_service.py` | Construcción de la lectura, el formato de fecha `dd/mm/YYYY` del ESP32, y el comportamiento del agregado |
| `test_ingest_use_case.py` | El caso de uso con dobles. Incluye la invariante clave: **si la nube está caída, la lectura NO se pierde** |
| `test_ingest_endpoint.py` | El contrato HTTP del que depende el firmware, con el cliente de test de Flask (sin abrir puertos) |
| `test_app_config.py` | Que el debug esté apagado por defecto |

El edge es la **autoridad de la clasificación**: el backend confía en el `level`
que llega de aquí y no reclasifica. Si estos tests se ponen rojos, toda la
plataforma está clasificando distinto.

## Endpoints
- `POST /api/v1/emf-monitoring/data-records` — ingesta del dispositivo (requiere `X-API-Key`).
- `GET  /api/v1/emf-monitoring/readings` — lista lo guardado localmente.
- `GET  /health` — estado.

## Credenciales del dispositivo de prueba (IAM)
- `device_id` (serial): `EMSAFE-6766-01`
- `X-API-Key`: `emsafe-edge-key-6766`

## Probarlo sin el ESP32
```bash
curl -X POST http://localhost:5000/api/v1/emf-monitoring/data-records ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: emsafe-edge-key-6766" ^
  -d "{\"device_id\":\"EMSAFE-6766-01\",\"field_uT\":250.4,\"plug\":\"OFF\",\"created_at\":\"19/06/2026 18:40:00\"}"
```
Respuesta esperada: el edge **clasifica** el nivel (`DANGER`), guarda local y, si el sync
está activo, lo manda a Azure.

## Activar la sincronización con Azure
Por defecto el sync está **apagado**. Para activarlo, define variables de entorno
(o edita `monitoring/infrastructure/cloud_sync.py`):
```bash
set EMSAFE_SYNC_ENABLED=true
set EMSAFE_BACKEND_EMAIL=admin@emsafe.com
set EMSAFE_BACKEND_PASSWORD=admin123
```
El edge hará `POST /api/auth/login` para obtener el JWT y luego enviará la lectura a
`POST /api/v1/readings` del backend (`serialNumber`, `level`, `message`, `field_uT`).

> Por seguridad, no dejes las credenciales en el repositorio — usa variables de entorno.

## Conectar el ESP32
En el `sketch.ino`:
- `ENDPOINT_URL` -> `http://<IP-LOCAL-DE-TU-PC>:5000/api/v1/emf-monitoring/data-records`
- Agregar el header `X-API-Key: emsafe-edge-key-6766`

**Wokwi** corre en la nube y no alcanza tu `localhost`: usa un túnel (ngrok) y esa URL pública.
Con el **dispositivo físico** en tu red WiFi, usa la IP local de tu PC.
