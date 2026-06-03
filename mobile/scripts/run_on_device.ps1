# Запуск на реальном Android (USB). Nothing Phone и др.
# Требования: Flask на 0.0.0.0, телефон в той же Wi‑Fi сети.
param(
    [int]$Port = 5001,
    [string]$DeviceId = ""
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Get-LanIPv4 {
    Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike '127.*' -and
            $_.IPAddress -notlike '169.254.*' -and
            $_.PrefixOrigin -ne 'WellKnown'
        } |
        Sort-Object InterfaceMetric |
        Select-Object -First 1 -ExpandProperty IPAddress
}

$ip = Get-LanIPv4
if (-not $ip) {
    Write-Host "Не удалось определить LAN IP. Укажите вручную:"
    Write-Host '  flutter run --dart-define=API_BASE_URL=http://192.168.x.x:5001'
    exit 1
}

$apiUrl = "http://${ip}:${Port}"
Write-Host "API_BASE_URL = $apiUrl"
Write-Host "Убедитесь: python app.py слушает 0.0.0.0:$Port и Windows Firewall разрешает вход."
Write-Host ""

flutter pub get

$args = @("run", "--dart-define=API_BASE_URL=$apiUrl")
if ($DeviceId) {
    $args += @("-d", $DeviceId)
}

flutter @args
