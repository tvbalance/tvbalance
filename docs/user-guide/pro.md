# TVBalance Pro

TVBalance is free for one TV. A **Pro license**, bought once for the whole household, removes the limit and
unlocks the advanced features as they arrive.

| | Free | Pro |
| --- | --- | --- |
| TVs supervised | 1 | Unlimited |
| Profiles and calendar | No | Yes |
| Advanced budgets (per weekday, app groups, rollover) | No | Yes |
| Rules, time budgets, parent actions, notifications, Home Assistant | Yes | Yes |

The license is a key you paste into the app. It is checked on your own device with a signature, so it needs no
internet connection and nothing about you is sent anywhere.

## Profiles and calendar

A **profile** is a rule set you switch on for the whole household at once, for example "Holidays" or
"Grandparents' weekend". While it is on, every TV follows it instead of its own rule set, except the TVs you leave
out (say, the parents' TV).

- **By hand:** in **Rules**, press *Activate as profile* on a set, choose how long (30 minutes to 4 hours, or until
  midnight) and the TVs to leave out. The Dashboard shows the active profile with an *End profile* button.
- **By the calendar:** in **Rules > Calendar**, add entries that switch a rule set on by themselves, either every
  week on chosen days and hours (a window that ends before it starts runs past midnight) or between two dates.
- **From Home Assistant:** the `tvbalance.activate_profile` and `tvbalance.stop_profile` services and the
  "calendar" blueprint.

When several apply, the most recent manual profile wins, then a dated calendar entry, then a weekly one, then the
TV's own rule set. Ending a profile or letting it expire returns every TV to its own rules.

You can set profiles and the calendar up on any plan; they are saved but only applied with a Pro license, and the
screens say so. Nothing is lost if a license ends.

## Advanced budgets

A rule set's daily budget can be refined in **Rules > Time**:

- **Budget by weekday:** a different number of minutes for any day, for example more on Saturday. A day left empty
  uses the daily budget.
- **App groups:** a group of apps, such as "Games", that share one daily allowance. When the group's time is used
  up its apps are blocked while everything else stays available, and a warning appears before it runs out. Pick the
  apps from the list read from the TV.
- **Carry over unused time:** minutes not used yesterday are added to today, up to a maximum you choose. Carried-over
  minutes never pile up from one day to the next.

They can be set up on any plan and are saved either way, but they are only applied with a Pro license; on Free the
plain daily budget applies. Nothing is lost if a license ends.

## Get and activate a license
1. In **Settings → TVBalance Pro**, choose **Buy Pro** (shown when the purchase page is configured).
2. After you pay you receive a license key: a long line of letters and digits with one dot in the middle.
3. Paste it into **License key** and choose **Activate**. Only the administrator sees this card.

The card then shows the plan, who the license is for, and the expiry date, if there is one. Most licenses never
expire.

## What happens on the Free plan with several TVs
You can always add and configure as many TVs as you like. On the Free plan only the **oldest enabled TV** is
supervised; the others keep their settings but are not watched, and are marked **Requires Pro**. Turn off the
oldest TV and the next one takes its place.

## Expiry and removal
Nothing is deleted when a license expires or you remove it. The household simply goes back to the Free plan, and
the extra TVs stop being supervised until a license is active again. A stored key that stops being valid (for
example after a key rotation) is treated the same way, and the card says so.

Removing the license is in **Settings → TVBalance Pro → Remove license**.
