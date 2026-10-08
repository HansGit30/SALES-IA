$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$backendRoot = Join-Path $projectRoot 'backend'
$frontendRoot = Join-Path $projectRoot 'frontend'
$pythonPath = Join-Path $backendRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pythonPath)) { throw 'Falta backend/.venv. Instala las dependencias del backend antes de iniciar.' }
if (!(Test-Path -LiteralPath (Join-Path $backendRoot '.env'))) { throw 'Falta backend/.env. Configura la conexion antes de iniciar.' }
if (!(Test-Path -LiteralPath (Join-Path $frontendRoot 'node_modules\vite\bin\vite.js'))) { throw 'Ejecuta npm install dentro de frontend.' }

$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (!$listener) {
    Start-Process -FilePath $pythonPath -ArgumentList '-m uvicorn app.main:app --host 127.0.0.1 --port 8000' -WorkingDirectory $backendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $backendRoot 'server.stdout.log') -RedirectStandardError (Join-Path $backendRoot 'server.stderr.log') | Out-Null
}
$healthy = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 2
        if ($health.service -ne 'salesia-api') { throw 'El puerto 8000 pertenece a otro servicio.' }
        $healthy = $true
        break
    } catch { Start-Sleep -Milliseconds 500 }
}
if (!$healthy) { throw 'El backend no pudo iniciar. Revisa backend/server.stderr.log y el puerto 8000.' }
try { $null = Invoke-RestMethod 'http://127.0.0.1:8000/ready' -TimeoutSec 20 }
catch { throw 'La API inicio, pero la base de datos no esta lista. Revisa la conexion y ejecuta las migraciones pendientes.' }

$frontendListener = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if (!$frontendListener) {
    $nodePath = (Get-Command node -ErrorAction Stop).Source
    Start-Process -FilePath $nodePath -ArgumentList 'node_modules/vite/bin/vite.js --host localhost --port 5173 --strictPort' -WorkingDirectory $frontendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $frontendRoot 'server.stdout.log') -RedirectStandardError (Join-Path $frontendRoot 'server.stderr.log') | Out-Null
}
Write-Host 'API y base de datos listas. Frontend: http://localhost:5173/'
Write-Host 'Los procesos quedan activos en segundo plano. No cierres Windows mientras trabajas.'
