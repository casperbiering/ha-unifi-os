# Agent notes

Home Assistant custom integration `unifi_os` for UniFi OS console and application **update status**. Not the official core `unifi` (Network) integration. Do not merge them.

## HACS / blueprint updates

Diff these when bumping scaffolding (devcontainer, scripts, hassfest/hacs workflow pins, ruff, `hacs.json` keys):

- Template HACS documents: https://github.com/ludeeus/integration_blueprint (`main`)
- `hacs.json` schema and layout: https://www.hacs.xyz/docs/publish/start/ and https://www.hacs.xyz/docs/publish/integration/
- CI bar for a later default-store listing: https://www.hacs.xyz/docs/publish/include/ (hassfest + `hacs/action`). We are **not** in `hacs/default`; keep those actions green anyway.
- Brand files live in `custom_components/unifi_os/brand/` (HA 2026.3 brands proxy). Do not PR `home-assistant/brands`. https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api/
- Tests: https://github.com/MatthewFlamm/pytest-homeassistant-custom-component
- Releases: https://python-semantic-release.readthedocs.io/

Do not copy [scaarup/aula](https://github.com/scaarup/aula) (zip_release, black, extra workflows). That template is older than the official blueprint.

## Product constraints

- Login with **aiounifi only**, then `GET /api/system` on the OS root. Do not use `api.request()` (it prefixes `/proxy/network`). Do not use the Network websocket `SYSTEM` channel for this integration.
- Status-only update entities. No INSTALL. Read-only UniFi accounts work if login + GET succeed.
- One console device: **name** = product (`os.model`, e.g. `UDM SE`), **model** = SKU (`os.shortname`). Not the hostname. Config entry title may still be the hostname.
- Unique ids: OS `unifi_os-{mac}`, apps `unifi_app-{mac}-{name}`. Uninstalled apps get no entity.
- Poll every 30 minutes.
- Version lives in `custom_components/unifi_os/manifest.json`. Python Semantic Release stamps it on a manual Release run.
- Keep `requirements.txt` and `manifest.json` `requirements` in lockstep. Libraries Home Assistant also ships use a minimum (`aiounifi>=…`); exact pins are for packages core does not ship (pytest plugin, ruff).
- Do not add a local “fake updates” preview overlay.
- Do not open a `hacs/default` PR unless explicitly asked.

## Commits and releases

Use Conventional Commits. Actions → **Release** → Run workflow.

Release authenticates as the GitHub App whose ID is `vars.RELEASE_APP_ID`. That App must stay on the `main` ruleset bypass list so python-semantic-release can push the version commit and tag. `GITHUB_TOKEN` cannot bypass.

- `feat:` minor, `fix:` / `perf:` patch, `BREAKING CHANGE:` or `type!:` major
- `chore:`, `docs:`, `ci:`, `refactor:`, `test:`, `style:` do not bump; they are included in the next feat/fix/breaking changelog
- Dependabot PRs use `chore(deps):` and do not bump

## Layout

- Integration: `custom_components/unifi_os/`
- Tests: `tests/` with `pytest-homeassistant-custom-component`
- Local HA: `scripts/develop` + `config/configuration.yaml`
