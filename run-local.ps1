

param(
    [string]$BackendUrl = "http://localhost:8080"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# 1) venv: crearlo + instalar deps la primera vez
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "[edge] Creando .venv e instalando dependencias (solo la 1ra vez)..." -ForegroundColor Yellow
    python -m venv .venv
    & $py -m pip install --disable-pip-version-check -q -r requirements.txt
}

# 2) Config LOCAL (esto es lo que evita que sincronice a Azure)
$env:EMSAFE_SYNC_ENABLED = "true"
$env:EMSAFE_BACKEND_URL  = $BackendUrl

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  EMSafe Edge  ->  LOCAL" -ForegroundColor Cyan
Write-Host "  Sync habilitado : $env:EMSAFE_SYNC_ENABLED"
Write-Host "  Backend destino : $env:EMSAFE_BACKEND_URL   (NO Azure)"
Write-Host "  Escuchando en   : http://localhost:5000"
Write-Host "  Endpoint ingesta: http://localhost:5000/api/v1/emf-monitoring/data-records"
Write-Host "==================================================" -ForegroundColor Cyan

# 3) Arrancar el edge
& $py app.py
