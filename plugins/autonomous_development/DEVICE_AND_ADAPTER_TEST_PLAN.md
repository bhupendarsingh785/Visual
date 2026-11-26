# VISUAL Device and Integration Test Adapters

Status: test contract only; this file is not evidence that a device or live-service test ran.

## Android / Termux device adapter
- Run on the target phone after explicit local launch.
- Capture Android API level, Termux and Termux:API versions, Python version, CPU architecture, available RAM/storage, battery/thermal state and permissions.
- Exercise read-only probes first; microphone/camera tests require interactive owner action.
- Record screen-on/off, Doze, network transition, process restart and reboot outcomes. Emulator evidence is distinct from physical-device evidence.
- Never report physical-device pass from mocked CI.

## Provider live-connectivity adapter
- For each configured provider, issue a minimal authenticated model-list or low-cost text smoke request using only the configured key.
- Redact credentials and response bodies; record provider, model, HTTP status, latency, timestamp, capability and sanitized error class.
- Distinguish missing key, DNS/TLS, 401/403, 404/model retired, 429/quota, 5xx and schema mismatch.
- No request without owner-configured credentials. Never persist raw authorization headers.

## App / browser / database / deployment adapters
- App: Android package presence, launch and intent result; emulator and physical reports separate.
- Browser: Playwright page load, console errors, navigation, accessibility smoke and network failures.
- API: HTTP contract tests with bounded request/response capture and test credentials.
- Database: temporary SQLite by default; service DB adapters use isolated test databases, migrations, constraints, rollback and integrity assertions.
- Deployment: dry-run/config validation, staging health checks and rollback verification. Production deploy pauses for owner approval.

## Evidence contract
Each adapter returns JSON containing status (passed/failed/unavailable), environment, timestamps, checks, limitations and sanitized evidence id. Missing hardware, credentials, services, browser binaries or Docker is unavailable, never passed.
