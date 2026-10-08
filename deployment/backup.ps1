param([string]$Destination = "backups")
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    $backupName = "salesia-" + (Get-Date -Format "yyyyMMdd-HHmmss") + "-" + ([guid]::NewGuid().ToString("N").Substring(0,8)) + ".dump"
    $targetPath = Join-Path (Resolve-Path -LiteralPath $Destination).Path $backupName
    $containerPath = "/tmp/" + $backupName
    & docker compose -f compose.release.yml exec -T db pg_dump -U salesia -d salesia -Fc -f $containerPath
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el respaldo." }
    & docker compose -f compose.release.yml cp ("db:" + $containerPath) $targetPath
    if ($LASTEXITCODE -ne 0) { throw "No se pudo copiar el respaldo. Permanece en $containerPath dentro del contenedor." }
    & docker compose -f compose.release.yml exec -T db rm -- $containerPath
    if ($LASTEXITCODE -ne 0) { Write-Warning "El respaldo local existe; no se pudo retirar la copia temporal del contenedor." }
    Write-Output "Respaldo creado: $targetPath"
    Write-Output "La restauración debe comprobarse en una base separada antes de considerar recuperable este respaldo."
}
finally { Pop-Location }
