# M9: Add-on release, Supervisor discovery, publishing

Status: done. Release steps that need the maintainers are in `docs/operations/release.md`.

## Goal
Make the product installable the Home Assistant way: the Add-on announces itself to Home Assistant (no URL or token
to copy), the client is published on PyPI so HACS can install the integration, and the release pipeline is ready.

## Product decisions
- `tvbalance-client` ships on PyPI through trusted publishing (OIDC). The PyPI project and publisher are created by
  the maintainers once.
- HTTPS on the LAN is out of scope and becomes M18.
- M9 prepares and verifies everything in CI without pushing. Tags, public visibility of the repository and packages,
  and the HACS mirror repository are manual steps listed in `docs/operations/release.md`.

## Engine
- `EngineConfig.supervisor_token` (`SUPERVISOR_TOKEN`) and `supervisor_url` (`TVBALANCE_SUPERVISOR_URL`, default
  `http://supervisor`). Discovery runs only when the token exists.
- `SecretSettingsStore`: settings values sealed with the existing `SecretBox`, exposed as `storage.secrets`.
- `HomeAssistantDiscovery`: keeps one API token (read + control) named "Home Assistant (Add-on)", creating a new one
  when it is missing or revoked, and posts `{host, port, token}` to the Supervisor `/discovery` endpoint. Runs as a
  background task with backoff (1 s to 60 s) until the Supervisor answers.

## Integration
`async_step_hassio` and `async_step_hassio_confirm`. The unique id is the URL, as in the manual flow, so an existing
entry is updated with the new token instead of duplicated. Translations in five languages.

## Add-on
`hassio_api: true`, `discovery: [tvbalance]`, build arguments and `io.hass.*` labels, rewritten `DOCS.md`, changelog.
Icons and logo wait for the brand and domain checks.

## Release
- One product version for the engine, the Add-on and the integration, checked by a test and by
  `scripts/check_release.py` against the tag. The client has its own version.
- `release.yml`: version check, images, HACS mirror (skipped without `HACS_MIRROR_TOKEN`).
- `publish-client.yml` on `client-v*` tags.
- CI: Add-on linter, client build with `twine check`, image build with `BUILD_VERSION`.

## Tests
Fake Supervisor over local HTTP (token created, reused, regenerated after revocation, payload, retry, disabled
without token); sealed settings round trip; config flow for discovery (create, update token, connection and auth
errors, already configured); version consistency.

## Commit sequence
1. Plan (this document).
2. Sealed secret settings.
3. Supervisor discovery in the Engine.
4. Integration discovery flow.
5. Add-on metadata, labels and docs.
6. Version consistency and release check.
7. Client packaging and PyPI workflow.
8. HACS mirror.
9. Release checklist, user guide, plan status.
