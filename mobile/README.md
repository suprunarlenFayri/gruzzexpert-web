# GruzzExpert B2B — Flutter (Android APK + iOS IPA)

Нативный клиент для Flask-бэкенда: REST `/api/mobile/*`, Socket.IO, FCM push.

## Требования

- Flutter SDK 3.16+ ([установка](https://docs.flutter.dev/get-started/install))
- Android Studio / Xcode для сборки
- Запущенный Flask (`python app.py`)

## Первичная настройка

```bash
cd mobile
flutter pub get
```

Если папки `ios/` или части `android/` неполные:

```bash
flutter create . --org ru.gruzzexpert --project-name gruzz_b2b
```

Скопируйте `google-services.json` (Firebase) в `android/app/`.

## API URL

Flask в этом проекте по умолчанию: **`python app.py` → `0.0.0.0:5001`**.

| Среда | URL |
|--------|-----|
| Эмулятор | `http://10.0.2.2:5001` |
| Реальный телефон (USB, та же Wi‑Fi) | `http://<LAN-IP-ПК>:5001` |

### Тест на Nothing Phone / USB-отладка

1. На ПК: `python app.py` (слушает `0.0.0.0:5001`).
2. Разрешите вход в **Брандмауэр Windows** для Python на порт 5001.
3. Телефон и ПК в одной Wi‑Fi сети, USB debugging включён.
4. В каталоге `mobile/`:

```powershell
flutter devices
.\scripts\run_on_device.ps1
```

Или вручную (узнайте IP: `ipconfig` → IPv4):

```bash
flutter run --dart-define=API_BASE_URL=http://192.168.1.10:5001
```

В debug-режиме внизу экрана показывается текущий `API_BASE_URL`.

Release:

```bash
flutter build apk --release --dart-define=API_BASE_URL=https://api.gruzzexpert.ru
```

## Release APK

1. Положите `google-services.json` в `android/app/` (Firebase Console → Android app `ru.gruzzexpert.b2b`).

2. Создайте keystore и `android/key.properties` (не коммитить):

```properties
storePassword=***
keyPassword=***
keyAlias=upload
storeFile=../upload-keystore.jks
```

3. Сборка с боевым URL (обязательно):

```bash
flutter build apk --release --dart-define=API_BASE_URL=https://ВАШ_БОЕВОЙ_ДОМЕН_ИЛИ_IP
```

Или PowerShell:

```powershell
.\scripts\build_release_apk.ps1 -ApiBaseUrl "https://192.168.1.10:5000"
```

APK: `build/app/outputs/flutter-apk/app-release.apk`

Эмулятор по умолчанию: `http://10.0.2.2:5001` (см. `lib/core/config/app_config.dart`).

## Push (FCM)

- `lib/services/notification_service.dart` — Firebase Messaging + `flutter_local_notifications` в foreground.
- После логина: `POST /api/mobile/fcm/register` с токеном устройства.
- Канал Android: `gruzz_b2b_high` (звук + вибрация).

## iOS IPA

```bash
flutter build ipa --release
```

(нужен Apple Developer, `GoogleService-Info.plist` в `ios/Runner/`)

## Бэкенд

- Миграция: `flask db upgrade`
- `.env`: `SMS_API_KEY`, `FIREBASE_CREDENTIALS_PATH=firebase_credentials.json`
- `pip install -r requirements.txt`

## Архитектура

| Модуль | Назначение |
|--------|------------|
| `lib/core/api/` | Dio + токен в `flutter_secure_storage` |
| `lib/core/socket/` | Socket.IO (Flask-SocketIO) |
| `lib/core/push/` | `firebase_messaging`, регистрация FCM на `/api/mobile/fcm/register` |
| `lib/features/auth/` | Телефон+пароль+SMS 4 цифры; создатель email+TOTP |
| `lib/features/chats/` | Список чатов, комната, отправка сообщений |
| `lib/features/tasks/` | Список заявок (пул + мои), карточка, взять/отказ/статусы |

`web_socket_channel` подключён для будущих raw WebSocket endpoint'ов; чаты используют `socket_io_client`.

### Mobile REST (Flask)

| Метод | Путь |
|-------|------|
| GET | `/api/mobile/chats` |
| GET | `/api/mobile/chats/<id>/messages` |
| POST | `/api/mobile/chats/<id>/send` |
| GET | `/api/mobile/tasks` |
| GET | `/api/mobile/tasks/<id>` |
| POST | `/api/tasks/<id>/status` (Bearer, те же действия что веб) |
