# Issuing Pro licenses

For maintainers. A license is an Ed25519 signature over a small JSON payload, verified offline by the Engine
against the public keys compiled into `TRUSTED_PUBLIC_KEYS` (`engine/src/tvbalance/infra/licensing.py`).
The design is in [ADR 0006](../architecture/adr/0006-open-core.md).

Key format: `base64url(payload).base64url(signature)`. The payload carries `v`, `product`, `tier`, `license_id`,
`licensee`, `issued_at` and an optional `expires_at` (absent means perpetual).

## One-time setup
1. Generate the production pair on a machine you trust, **outside the repository**:

   ```
   uv run python scripts/license.py keygen --out <private-dir>
   ```

   It writes `license-private.pem` (permissions restricted, never overwritten) and prints the public key.
2. Store the private key offline (password manager or encrypted backup). Anyone holding it can mint licenses, and
   it cannot be recovered if lost.
3. Add the printed public key to `TRUSTED_PUBLIC_KEYS` and release.

## Issue a license
```
uv run python scripts/license.py sign --private-key <private-dir>/license-private.pem --licensee "Name"
uv run python scripts/license.py sign --private-key <pem> --licensee "Name" --expires 2027-12-31
```

The command prints the key; send it to the buyer. `--license-id` sets your own order reference, otherwise a UUID
is generated. Keep a record of issued ids and licensees yourself; the Engine never contacts a server.

## Rotate the key
Add the new public key **next to** the old one in `TRUSTED_PUBLIC_KEYS`, release, and sign new licenses with the
new private key. Existing licenses keep working until you drop the old public key; a customer whose key stops
verifying falls back to Free and sees "no longer valid" in Settings.

## Purchase page
Set `TVBALANCE_CHECKOUT_URL` to an `http(s)` URL to show the **Buy Pro** button. Without it no button is shown.
