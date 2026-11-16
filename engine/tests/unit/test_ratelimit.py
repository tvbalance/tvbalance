import pytest
from support import FakeClock

from tvbalance.app.ratelimit import RateLimiter


def limiter(clock: FakeClock, **kwargs: float) -> RateLimiter:
    return RateLimiter(clock, free_attempts=2, base_delay=1.0, max_delay=8.0, **kwargs)


def test_a_few_failures_are_free() -> None:
    clock = FakeClock()
    rl = limiter(clock)
    rl.failure("ip")
    rl.failure("ip")
    assert rl.retry_after("ip") == 0


def test_the_delay_doubles_with_each_further_failure() -> None:
    clock = FakeClock()
    rl = limiter(clock)
    for _ in range(2):
        rl.failure("ip")
    delays = []
    for _ in range(3):
        rl.failure("ip")
        delays.append(rl.retry_after("ip"))
        clock.advance(seconds=delays[-1])
    assert delays == [1, 2, 4]


def test_the_delay_is_capped() -> None:
    clock = FakeClock()
    rl = limiter(clock)
    for _ in range(12):
        rl.failure("ip")
    assert rl.retry_after("ip") == 8


def test_the_lock_runs_out_with_time() -> None:
    clock = FakeClock()
    rl = limiter(clock)
    for _ in range(3):
        rl.failure("ip")
    assert rl.retry_after("ip") == 1
    clock.advance(seconds=0.4)
    assert rl.retry_after("ip") == pytest.approx(0.6, abs=1e-3)
    clock.advance(seconds=0.6)
    assert rl.retry_after("ip") == 0


def test_success_forgets_the_failures() -> None:
    clock = FakeClock()
    rl = limiter(clock)
    for _ in range(5):
        rl.failure("ip")
    rl.success("ip")
    assert rl.retry_after("ip") == 0
    rl.failure("ip")
    assert rl.retry_after("ip") == 0


def test_keys_do_not_affect_each_other() -> None:
    clock = FakeClock()
    rl = limiter(clock)
    for _ in range(5):
        rl.failure("a")
    assert rl.retry_after("a") > 0
    assert rl.retry_after("b") == 0


def test_old_failures_are_forgotten() -> None:
    clock = FakeClock()
    rl = limiter(clock, forget_after=60.0)
    for _ in range(5):
        rl.failure("ip")
    clock.advance(seconds=61)
    assert rl.retry_after("ip") == 0
    rl.failure("ip")
    rl.failure("ip")
    assert rl.retry_after("ip") == 0  # counting restarted from zero


def test_memory_is_bounded() -> None:
    clock = FakeClock()
    rl = limiter(clock, max_keys=3)
    for i in range(10):
        rl.failure(f"ip{i}")
        clock.advance(seconds=1)
    assert rl.tracked() <= 3
