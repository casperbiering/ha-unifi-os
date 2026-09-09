# UniFi OS for Home Assistant

Custom integration that shows **UniFi OS firmware** and **installed application** update status on a UniFi OS console (UDM, Cloud Gateway, and similar).

This is **not** the official [UniFi Network](https://www.home-assistant.io/integrations/unifi/) integration. Keep both: Network still owns clients, device firmware, and site controls. This integration only reads Control Plane update state.

Entities are **status-only**. There is no install action, so a read-only UniFi local user works if login and `GET /api/system` succeed.

## Install with HACS (custom repository)

This repository is not in the HACS default store. Add it as a custom repository:

1. Open **HACS**.
2. Open the three-dot menu and choose **Custom repositories**.
3. URL: `https://github.com/casperbiering/ha-unifi-os`
4. Type: **Integration**
5. Add the repository, then download **UniFi OS**.
6. Restart Home Assistant and add the integration from Settings → Devices & services.

[![Open your Home Assistant instance and show the add custom repository dialog with a specific repository pre-filled.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=casperbiering&repository=ha-unifi-os&category=integration)

Requires Home Assistant 2026.6.0 or newer, HACS 2.0.5 or newer, and a UniFi OS console (not a self-hosted Network application).

## What you get

- One device for the console. The name is the product (for example `UDM SE`); the model is the SKU (for example `UDMPROSE`).
- A **Firmware** update entity for UniFi OS.
- An update entity for each **installed** application (Network, Protect, Access, and so on). Uninstalled apps are omitted.

The integration logs in with [aiounifi](https://github.com/Kane610/aiounifi), then polls `GET /api/system` every 30 minutes.

## Releases

GitHub Releases are the versions HACS offers. Maintainers run **Actions → Release → Run workflow**. Version bumps follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` minor
- `fix:` patch
- `BREAKING CHANGE:` / `feat!:` major
- `chore:`, `docs:`, `ci:` do not bump; they appear in the next feat/fix/breaking notes

## Development

Open this repository in a VS Code / Cursor devcontainer, then:

```bash
scripts/setup
scripts/develop   # Home Assistant on port 8123
scripts/lint
python3 -m pytest
```
