# Troubleshooting

Start with the dashboard: each TV card says whether the TV is on, unreachable or **Needs pairing**. **Activity**
shows the latest events, such as connection problems, in plain words.

## The TV is not found
- Check that the TV is on and on the same network as TVBalance, not on a guest network.
- Some routers block the discovery messages between devices. Choose the brand under *Enter the address* in the
  wizard and type the TV's IP address, found in the TV's network settings.
- With Docker on Windows or macOS, discovery cannot work because the container sits behind a virtual network. Enter
  the address by hand. See [Install](install.md).
- Give the TV a fixed address in your router (a DHCP reservation), so the address you typed stays valid.
- For LG TVs, check the settings in [LG webOS](tv-lg-webos.md).

## Pairing does not finish
- Keep the remote at hand and accept the request on the TV within three minutes. The TV shows it only while it is
  switched on.
- If you pressed **No**, or nothing happened, use **Try again** in the wizard.
- Make sure the TV is not showing another full-screen prompt or a screensaver.

## The card says "Needs pairing"
The TV forgot the key TVBalance holds, for example after a factory reset or a software update. Open **Pair again** on
the card and accept the request on the TV once more. Rules, history and settings are kept. With Web Push on, you also
get a notification when this happens.

## The TV is "unreachable"
TVBalance cannot connect to the TV, which is normal when the TV is unplugged. If it happens while the TV is on:

- Check the TV's address in your router. If it changed, remove the TV and add it again with its new address, or give
  it a fixed address.
- Check that the TV's network features are still enabled (for LG, see [LG webOS](tv-lg-webos.md)).
- Restart the TV completely (unplug it for a minute). Some TVs stop answering after long uptime.

## A rule does not seem to apply
- Check that the TV has monitoring on (the TV's details page) and that it follows the rule set you edited.
- On LG TVs with **Quick Start+**, a TV with the screen off reports standby, so the daily budget does not run. This is
  expected. See the limits in [LG webOS](tv-lg-webos.md).
- A manual **Allow** or **Block** overrides the rules until it ends. Use **Clear override** on the card.
- Profiles, the calendar and advanced budgets are saved on every plan but applied only with
  [Pro](pro.md). The screens say so.
- Times follow the time zone chosen at setup, not the TV's clock. Check it in **Settings → General**.

## The browser warns that the connection is not private
The secure address uses a certificate from a small authority that TVBalance created. Your device has to trust it
once. Follow [HTTPS on your network](https.md): download the certificate in **Settings → Secure connection**, install
it, and compare the fingerprint. Firefox keeps its own list, so import it there too.

## No notifications on the phone
Browsers allow push notifications only on a secure connection.

- Open the web app through Home Assistant over HTTPS, or through the secure address of TVBalance, not through a plain
  `http://` address. The card in **Settings → Notifications** links to the secure address when there is one.
- On iPhone and iPad, add TVBalance to the Home Screen first and turn notifications on from that icon.
- Send a test from the same card. If it does not arrive, allow notifications for the site or app in the phone's
  settings.

## Home Assistant does not find TVBalance
- With the Add-on, restart it and look under **Settings → Devices & services** for the **TVBalance** notification.
- If you revoked the token "Home Assistant (Add-on)" in **Settings → API tokens**, restart the Add-on: it creates a
  new one.
- With a standalone Engine, check the address, the port and that the token has the **read** and **control** scopes.
  See [Home Assistant](home-assistant.md).

## A PIN is rejected
After five wrong PINs, PIN sign-in locks for a while. Wait, or sign in with the administrator password and change the
PIN in **Settings → Security**.

## Forgotten administrator password
TVBalance has no password reset yet, because nothing is sent outside your home. If a browser is still signed in, you
can change the password in **Settings → Security**. If none is, the only way today is to start over with an empty
data folder: rules, history and the stored TV keys are lost and every TV has to be paired again. Restore a backup
made before the password was lost if you have one.

## Still stuck
Open an issue at <https://github.com/tvbalance/tvbalance/issues> and attach the diagnostics download. Do not post
tokens, license keys or the contents of the data folder.
