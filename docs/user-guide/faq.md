# Frequently asked questions

## Does TVBalance need an account or the internet?
No. It runs on your own network and talks to the TV directly. There is no cloud account and no telemetry. The Pro
license is a signed key checked on your device, so it needs no connection either.

## Where is my data?
In the data folder of the Engine (`/data` in the Add-on and in Docker): the database `tvbalance.db` with TVs, rules,
usage history and events, and `secret.key`, which protects the stored TV credentials. The Add-on's data is part of
Home Assistant backups. Keep the database and the key together.

## Which TVs are supported?
LG webOS 4 and newer is supported and verified on real hardware. Roku, Google/Android TV and Samsung Tizen are
planned and not usable yet. Each brand can do a different set of things, and the app only offers what the TV can
actually do. See [LG webOS](tv-lg-webos.md) for what an LG supports.

## Does it work without Home Assistant?
Yes. The web app works on its own, with Docker or the Add-on. Home Assistant adds entities, services, events and
blueprints for automations. See [Install](install.md) and [Home Assistant](home-assistant.md).

## What is free and what is Pro?
One TV with all the basic rules (schedules, daily budgets, app, input and channel blocking, parent actions,
notifications, Home Assistant) is free. Pro is a one-time license for the household that allows more TVs, profiles
and a calendar, advanced budgets, long history and weekly reports. See [TVBalance Pro](pro.md).

## What happens if my Pro license expires?
Nothing is deleted. Pro settings stay saved and stop being applied: the TVs beyond the first are no longer
supervised, and the rules fall back to the basic ones. Add a valid license and they apply again.

## Can my child get around it?
TVBalance acts on the TV, so a phone or a different remote does not help. It is a family tool, not a lock: a child
with the TV's own settings menu can still unplug it or change the network. Use the TV's PIN, and a PIN for TVBalance's
parent controls on shared devices. Signing in to change rules needs the administrator password.

## Can I use several TVs?
Yes, with [Pro](pro.md). Each TV follows one rule set, and several TVs can share the same set.

## Which languages are available?
English, Italian, German, French and Spanish. The web app follows your browser or Home Assistant, and you can change
it in **Settings → General**. This documentation is available in the same five languages.

## Does it work over HTTPS?
Yes. HTTPS is on by default with a certificate from a local authority that your devices trust once. You can also use
your own certificate. See [HTTPS on your network](https.md).

## How do I update?
With the Add-on, update it from the Add-on Store. With Docker, pull the new image and recreate the container. Your
data and settings are kept and the database is upgraded on start.

## How do I report a problem or ask for a TV brand?
Open an issue at <https://github.com/tvbalance/tvbalance/issues>. Attach the diagnostics download, and do not post
tokens or license keys. Developers can add a brand themselves with an adapter package.
