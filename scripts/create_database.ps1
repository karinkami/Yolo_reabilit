# Создать таблицы и сид вручную (без запуска сайта).
# Запуск из любой папки:  powershell -File scripts\create_database.ps1
# Или из корня проекта:   .\scripts\create_database.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = Join-Path $Root "yolo_env\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "Не найден venv: $Python" -ForegroundColor Red
    Write-Host "Сначала: python -m venv yolo_env" -ForegroundColor Yellow
    Write-Host "         .\yolo_env\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "         pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

& $Python (Join-Path $Root "scripts\init_database.py")
exit $LASTEXITCODE
