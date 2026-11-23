# Getting started

From a fresh install to a TV that follows your rules takes about five minutes. You need TVBalance
[installed](install.md) and your TV switched on, on the same network.

## 1. Open the web app
Open the **TVBalance** panel in Home Assistant, or `http://<address-of-the-machine>:8765` if you use Docker. The
first visit starts the setup.

## 2. Set up the household
The app asks for three things:

1. **A password** for the administrator, at least 10 characters. Keep it safe.
2. **Language and time zone.** Schedules and daily limits follow this time zone.
3. **A first rule set.** Start from "School days" or from an empty set. You can change everything later.

## 3. Add your TV
Choose **Add a TV**. The wizard searches your network and lists the TVs it finds. If yours is missing, enter its
address by hand. Follow the steps for your brand, for example [LG webOS](tv-lg-webos.md): the TV asks you to accept
the new device, and you do that once with the remote.

Name the TV and pick the rule set it should follow. That is all: the TV card on the dashboard now shows what is
playing, how many minutes were watched and how many are left.

## 4. Check that it works
- Open an app that your rules block, or wait for the end of an allowed window. TVBalance shows a message on the
  TV and sends it back to the home screen, or switches it off, depending on the rule set.
- Try **Pause** on the TV card: enforcement stops for 30 minutes.
- Try **Bonus** to add 15 or 30 minutes to today's budget.

## 5. Connect Home Assistant
With the Add-on, confirm the **TVBalance** notification under **Settings → Devices & services**. Every TV becomes a
device with sensors, a pause button and events you can use in automations. See
[Home Assistant](home-assistant.md).

## 6. Use it from your phone
For notifications on your phone and an app-like icon, open the secure address and trust the certificate once. See
[HTTPS on your network](https.md).

## Where to go next
- [The web app](web-ui.md): rules, the dashboard, activity and settings in detail.
- [TVBalance Pro](pro.md): profiles, a calendar, advanced budgets and reports.
- [Troubleshooting](troubleshooting.md) if the TV is not found or the connection is lost.
