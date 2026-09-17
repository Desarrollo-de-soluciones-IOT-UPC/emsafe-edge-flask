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
  con el VO `AlertLevel`, persiste en SQLite y **sincroniza** con la nube por el puerto
  `CloudSyncPort`.
- **shared/** — base de datos SQLite compartida (Peewee).

### Capas de `monitoring/`
```
domain/         value_objects.py  MagneticField · AlertLevel  (los umbrales viven aquí)
                entities.py       EmfReading (aggregate root)
                services.py       EmfReadingService — convierte el dato crudo en lectura
                ports.py          CloudSyncPort (puerto de salida)
application/    EmfMonitoringApplicationService — el caso de uso de ingesta
infrastructure/ repositories.py (SQLite) · cloud_sync.py (adaptador del puerto)
interfaces/     los endpoints REST
```

## Context map: edge ↔ nube

Los dos lados usan **los mismos nombres de contexto** (`iam`, `monitoring`) y el mismo
lenguaje: `MagneticField`↔`value` en µT, `AlertLevel`↔`RadiationLevel`,
`EmfReading`↔`RadiationReading`.

La relación es **Conformist**: el edge se adapta al contrato que publica el backend
(`POST /api/v1/readings`, `GET /api/v1/devices/{serial}/plug`, respuestas envueltas en
`ApiResponse`) sin negociarlo ni traducirlo. Toda esa conformidad está encapsulada en
`monitoring/infrastructure/cloud_sync.py`, que es el único archivo que cambia si el
backend cambia su API.

**Quién manda en el nivel de alerta:** el edge. Los umbrales (100 / 200 µT) están en
`monitoring/domain/value_objects.py`. El backend tiene los mismos números en
`RadiationLevel`, pero **no reclasifica**: respeta el nivel que llega y solo clasifica
por valor cuando la lectura viene sin nivel (datos antiguos o de semilla). Si los
umbrales cambian, se cambian en el edge.

El firmware (`firmware/sketch.ino`) tiene su propia copia de los umbrales, y eso es
correcto: necesita encender el LED y cortar el relé **sin red**. Su decisión es local e
inmediata; la alerta oficial del sistema la emite el edge.

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

> El modo debug de Flask va **apagado** por defecto: su consola permite ejecutar código
> arbitrario en el equipo del edge. Para depurar, `set EMSAFE_EDGE_DEBUG=true` — nunca
> en una demo ni en el prototipo físico.

> En IntelliJ: abre la carpeta, configura un intérprete de Python (con el venv),
> y dale Run a `app.py`.

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
