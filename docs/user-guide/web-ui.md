# The web app

TVBalance's web app runs in any browser on your home network, and inside Home Assistant as a side panel. It works well
on a phone, and installs to the home screen like an app. It speaks English, Italian, German, French and Spanish.

## First start
On the first visit the app asks for three things:
1. **A password** for the administrator (at least 10 characters). Keep it safe; it opens everything.
2. **Language and time zone.** Schedules and daily limits follow this time zone.
3. **A first rule set**, starting from "School days" (weekdays 16:00-20:00, weekends 09:00-21:00, two hours a day,
   warnings at 10 and 5 minutes) or from an empty set. Everything can be changed afterwards.

## Adding a TV
With no TV yet, the dashboard offers **Add a TV** (administrators only; a PIN session never sees it). The wizard
searches your network, or takes the TV's address by hand, then walks you through accepting the connection on the TV
and finishes by naming the TV and choosing its rule set. A TV that lost its key shows **Needs pairing** with a
**Pair again** link. Brand-specific steps are in the TV guides, such as [LG webOS](tv-lg-webos.md).

## Signing in
- **Password:** full access.
- **PIN:** an optional short code for a shared device, such as a tablet in the kitchen. A PIN session can look at the
  dashboard and use the parent controls, but cannot change rules, passwords or tokens. After five wrong PINs it locks
  for a while.
- Inside Home Assistant you are already signed in through Home Assistant.

## Dashboard
One card per TV shows whether it is on, what is playing, how many minutes were watched and how many are left, and
whether the current content is allowed. The card updates by itself.

Parent controls on each card:
- **Pause** stops enforcement for 30 minutes.
- **Bonus** adds 15 or 30 minutes to today's budget.
- **Allow** or **Block** overrides the rules for 15, 30, 60 or 120 minutes, or until midnight.
- **Clear override** returns to the rules.

## Rules
A rule set says when and for how long a TV may be used. Several TVs can share a set, and each TV follows one.
Open **Rules**, pick a set (or create one), and edit it in four tabs:

- **Schedule:** the time windows for each weekday. Add as many windows as you need, copy one day to others, and add
  special days for a single date such as a holiday. A window that ends before it starts runs past midnight.
- **Time:** an optional daily budget in minutes, and the warnings shown when that many minutes are left. With Pro
  you can also set a budget for each weekday, shared allowances for groups of apps, and carry unused time over to
  the next day. See [TVBalance Pro](pro.md).
- **Content:** apps, inputs and channels to block; an "only allow chosen apps" mode; things that are always allowed;
  and where the TV goes when something is blocked (home screen, an app, an input or a channel). Pick items from the
  list read from the TV, with app icons. If the TV is off or unreachable, type the ids by hand instead.
- **Advanced:** how firmly blocks are enforced. The defaults suit nearly everyone.

### Profiles and calendar (Pro)
*Activate as profile* on a rule set puts it in force for every TV in the household for a chosen time, leaving out
the TVs you tick. The Dashboard shows the profile in force and lets you end it; each TV card shows its name.
**Rules > Calendar** lists the entries that switch rule sets on automatically, weekly or between two dates. See
[TVBalance Pro](pro.md).

If a rule set can't be saved, a message names the problem, for example a fallback that is itself blocked, a warning
longer than the budget, or two overlapping windows.

## TV details and activity
Choose a TV's name on the dashboard to rename it, switch monitoring on or off, change its rule set, see the last seven
days as bars, and read its latest events. Removing a TV asks for confirmation.

**Activity** shows the same for all TVs, with a filter and the full event log: warnings, blocks, switch-offs and
connection problems.

Changing rules, TVs and settings needs the administrator password.

When you open the web app through a plain `http://` address and the Engine serves HTTPS, a banner offers the
secure address. You can dismiss it; the choice is remembered in this browser.

## Settings
- **General:** language, time zone and light/dark appearance.
- **Notifications:** get a push notification on this device when the TV needs pairing again, can't be reached,
  has content blocked, or is about to run out of time. Choose which of these you want, send a test, turn them off,
  and remove other devices. Only the administrator sees this card. Browsers allow push only on a secure
  connection, so it works through Home Assistant over HTTPS (Ingress), from `localhost` or from the secure
  address of your network (see https.md), not from a plain `http://` address. The card links to the secure
  address when there is one. On iPhone and iPad, add TVBalance to the Home Screen first.
- **TVBalance Pro:** the current plan, who the license is for and when it expires, a field to paste a license
  key, and a button to remove it. Only the administrator sees this card. See pro.md.
- **Secure connection:** the HTTPS addresses, the certificate's expiry and fingerprint, downloads of the
  certificate and of the iPhone and iPad profile, install steps per device, and a button to create a new
  certificate. Only the administrator sees this card. See https.md.
- **Security:** change the password; set or remove the parent PIN.
- **Signed-in devices:** see every signed-in browser and sign out any of them, or all but this one.
- **API tokens:** for other programs. A token's secret is shown once when you create it, so copy it right away.
  Choose **read** and **control** for Home Assistant (see home-assistant.md). Revoke a token at any time.

**System** shows the version and the TV brands this release supports, with their maturity.
