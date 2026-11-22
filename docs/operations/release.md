# Releasing TVBalance

Nothing here runs by itself: a release starts when a maintainer pushes a tag. The pipeline is checked in CI on every
push (image build, Add-on linter, client build with `twine check`, version consistency), so a tag only publishes.

## Versions

- **Product** (`vX.Y.Z`): one number in `engine/pyproject.toml`, `engine/src/tvbalance/__init__.py`,
  `addon/tvbalance/config.yaml` and `ha/custom_components/tvbalance/manifest.json`.
- **Client** (`client-vX.Y.Z`): `client/pyproject.toml`. The integration manifest pins it as
  `tvbalance-client==X.Y.Z`.

`python scripts/check_release.py [tag]` verifies all of this; CI and the release workflows run it.

## One-time setup

1. Make the repository public (Supervisor and HACS cannot read a private one).
2. **PyPI**: create the project `tvbalance-client` and add a trusted publisher (owner `tvbalance`, repository
   `tvbalance`, workflow `publish-client.yml`, environment `pypi`). Create the `pypi` environment in the repository.
3. **HACS mirror**: create an empty public repository `tvbalance/tvbalance-ha` and a token with write access to
   it; store it as the repository secret `HACS_MIRROR_TOKEN`. Without the secret the mirror job is skipped.
4. After the first release, make the ghcr packages `tvbalance`, `tvbalance-addon-amd64` and
   `tvbalance-addon-aarch64` public (package settings, **Change visibility**) so the Supervisor can pull them.

## Each release

1. Update `addon/tvbalance/CHANGELOG.md`, bump the versions, run `python scripts/check_release.py`, merge to `main`
   with CI green.
2. If the client changed, tag `client-vX.Y.Z` first and wait for PyPI: the integration cannot be installed before
   its pinned client exists.
3. Tag `vX.Y.Z`. The workflow publishes the images (multi-arch `tvbalance`, plus the per-architecture Add-on
   images) and mirrors the integration to `tvbalance-ha`.
4. Check: add the repository to a Home Assistant Add-on store, install the Add-on, and confirm the discovery
   notification and the integration setup.

## Not covered yet

Icons and logo (waiting for the brand and domain checks).

Before the first release that includes HTTPS (M18), also check by hand: install the CA on a phone and a computer,
open the secure address without warnings, turn on notifications and send the test, and confirm the fingerprint
in the Home Assistant integration setup over `https://`.
