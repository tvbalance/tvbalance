from datetime import UTC, datetime, timedelta

from tvbalance.infra.clock import SystemClock


def test_the_system_clock_is_aware_and_current() -> None:
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert abs(datetime.now(UTC) - now) < timedelta(seconds=5)
