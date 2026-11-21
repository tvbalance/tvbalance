# LG webOS TVs

TVBalance talks to LG TVs (webOS 4 and newer) over your home network. Nothing leaves your house.

## Prepare the TV
1. Connect the TV to the same network as the machine running TVBalance.
2. Enable **Settings > General > External Devices > TV On With Mobile > Turn on via Wi-Fi** (named *LG Connect Apps* on
   older models). The TV then accepts connections from other devices.
3. Give the TV a fixed address in your router (a DHCP reservation) so it stays reachable.

## Pair
1. Turn the TV on, keep the remote at hand, and open **Add a TV** in the web app.
2. Pick your TV from the list. If it is not listed (some networks block the search), choose **LG webOS** under
   *Enter the address* and type the TV's IP address, found in the TV's network settings.
3. Press **Start pairing** and watch the TV: it asks whether to allow the new device. Accept it with the remote within
   three minutes. TVBalance stores the key the TV hands out; you only do this once per TV.
4. Name the TV and choose its rule set.

If you press **No**, or nothing happens, use **Try again**. When the TV forgets the key (for example after a factory
reset) the dashboard shows **Needs pairing**: open **Pair again** on its card and accept once more.

## What TVBalance can do on an LG
Read what is playing (app, HDMI input, live channel and programme), list apps, inputs and channels, show an
on-screen message, go to the home screen, open an app, input or channel, and turn the TV off.

## Known limits
- **Quick Start+**: with this option the TV keeps answering while the screen is off. TVBalance reports it as standby,
  not as watching, so the daily budget does not run.
- **Programme titles** are only available while live TV is in the foreground, and not at all on webOS 4.5 and older.
- **Turning the TV on** is not supported yet.
- App icons are served by the TV with a self-signed certificate; the web app will show them through its own proxy.
