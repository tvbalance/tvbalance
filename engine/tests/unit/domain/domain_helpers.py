from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from tvbalance.domain.models import Observation, Power, Schedule, TimeWindow

ROME = ZoneInfo("Europe/Rome")
DAY = date(2026, 1, 5)  # a Monday


def at(clock: str, day: date = DAY) -> datetime:
    return datetime.combine(day, time.fromisoformat(clock), tzinfo=ROME)


def always_open() -> Schedule:
    return Schedule(windows={d: (TimeWindow(time(0), time(0)),) for d in range(7)})


def window(start: str, end: str) -> Schedule:
    win = TimeWindow(time.fromisoformat(start), time.fromisoformat(end))
    return Schedule(windows={d: (win,) for d in range(7)})


def tv(power: Power = Power.ON, now: datetime | None = None, **fields: str) -> Observation:
    return Observation(observed_at=now or at("18:00"), power=power, **fields)
