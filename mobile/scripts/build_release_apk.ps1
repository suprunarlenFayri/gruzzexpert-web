# Production APK с боевым API (замените URL).
param(
    [string]$ApiBaseUrl = "https://api.gruzzexpert.ru"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "Building release APK with API_BASE_URL=$ApiBaseUrl"
flutter pub get
flutter build apk --release --dart-define=API_BASE_URL=$ApiBaseUrl

Write-Host ""
Write-Host "APK: build\app\outputs\flutter-apk\app-release.apk"
