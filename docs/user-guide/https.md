# HTTPS on your network

TVBalance can answer over HTTPS on your home network. Browsers then treat the web app as secure: Web Push
notifications work, the sign-in cookie is marked `Secure`, and your password is no longer sent in clear.

HTTPS is on by default. The Engine listens on two ports:

| Port | Protocol | Used for |
| ---- | -------- | -------- |
| 8765 | HTTP     | Home Assistant Ingress, the health check, Add-on discovery, and a first look from a browser |
| 8766 | HTTPS    | The web app and the API on your network |

HTTP stays open on purpose. When you open the web app through `http://`, a banner offers the secure address, and the
Notifications card links to it.

## The certificate

A web address on your own network (`tvbalance.local`, `10.x.x.x`) cannot get a certificate from a public authority.
TVBalance therefore creates a small **local certificate authority** (CA) the first time it starts, and signs its own
server certificate with it. The server certificate lasts 397 days and is renewed by itself 30 days before it
expires, without a restart. It also changes when the Engine's name or address changes.

Your devices must trust the CA once. Until then a browser warns that the connection is not private.

### Install the CA on a device

Open **Settings → Secure connection** in the web app. It lists the secure addresses, the certificate's expiry and its
**fingerprint**, and offers two downloads: the certificate (`.crt`) and an iPhone and iPad profile.

Compare the fingerprint the device shows with the one in Settings before you trust it.

- **iPhone and iPad:** open the profile, allow it in Settings, install it, then turn it on in
  Settings → General → About → Certificate Trust Settings.
- **Android:** Settings → search for "CA certificate" → Install anyway → pick the downloaded file.
- **Windows:** open the file → Install Certificate → Local Machine → Trusted Root Certification Authorities.
- **macOS:** open the file in Keychain Access, then set Trust to Always Trust.

On Windows and Linux some browsers keep their own list of authorities (Firefox does): import the file there too.

### Start over with a new CA

**Create a new certificate** in the same card makes a new CA and a new server certificate. Use it if a device that
trusted the old CA is lost or you suspect the CA key leaked. Every device must then install the new CA, and the Home
Assistant integration asks you to confirm the new fingerprint.

## Your own certificate

If you already have a certificate that your devices trust (for example one made for Home Assistant), point TVBalance
at it instead:

- Standalone Engine: set `TVBALANCE_TLS_CERTFILE` and `TVBALANCE_TLS_KEYFILE` to the certificate chain and the
  private key, both PEM files.
- Home Assistant Add-on: put the files in the `/ssl` folder and set **Certificate file** and **Key file** in the
  Add-on options (for example `fullchain.pem` and `privkey.pem`).

The Engine checks that the key matches the certificate and that it has not expired. Settings → Secure connection then
only shows the status, because renewal is up to you. Restart the Engine after you replace the files.

## Settings

| Environment variable | Add-on option | Meaning |
| -------------------- | ------------- | ------- |
| `TVBALANCE_TLS` | HTTPS | `auto` (default) or `off` |
| `TVBALANCE_HTTPS_PORT` | | Port for HTTPS, 8766 by default (must differ from `TVBALANCE_PORT`) |
| `TVBALANCE_TLS_CERTFILE`, `TVBALANCE_TLS_KEYFILE` | Certificate file, Key file | Your own certificate |
| `TVBALANCE_TLS_NAMES` | Extra names | More host names or addresses for the automatic certificate, separated by commas |

Environment variables win over Add-on options.

The automatic certificate covers `localhost`, the machine's host name and its `.local` name, and its private IPv4
address. Names that are not local are left out, and Settings tells you which.

If the HTTPS port is busy, the Engine logs an error and keeps serving HTTP.

## Home Assistant

Over HTTP inside the Add-on nothing changes. To connect the integration through HTTPS, enter an `https://` address
and the API token. When the Engine's certificate is not trusted, the integration downloads the CA, shows its
fingerprint and asks you to compare it with Settings → Secure connection. After you confirm, Home Assistant accepts
only that CA for this Engine. If the CA changes later, a reauthentication asks you to confirm again.

## Security notes

- **What the CA can sign.** The CA carries X.509 Name Constraints: it can only issue certificates for `localhost`,
  `.local`, `.lan`, `.home.arpa`, `.internal` and private address ranges. A device that trusts it is not exposed to a
  forged certificate for a public site, as long as the client enforces name constraints (current browsers and
  operating systems do).
- **Where the key lives.** The CA key is stored sealed with the Engine's other secrets (`secret.key`), and the server
  key is a file with owner-only permissions in the data folder. Anyone who can read the data folder can issue
  certificates for local names, so protect it like the rest of your backups.
- **The download is public.** The CA certificate (never its key) can be downloaded without signing in, because a new
  device needs it before it can trust anything. Always confirm the fingerprint: it is the check that the file came
  from your Engine.
- **HTTP is still available.** Sign in through HTTPS on shared networks. The banner is there to remind you.
