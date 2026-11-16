from domain_helpers import always_open, tv

from tvbalance.domain.models import (
    Allow,
    AppTarget,
    Block,
    BlockReason,
    ChannelTarget,
    EnforcementLevel,
    GoHome,
    HomeTarget,
    InputTarget,
    LaunchApp,
    LimitKind,
    MessageKind,
    Policy,
    PowerOff,
    SetChannel,
    SetInput,
    ShowMessage,
    Warn,
)
from tvbalance.domain.rules import plan_actions
from tvbalance.sdk.types import Capability as C

ALL = set(C)
NOTIFY, REDIRECT, OFF = (
    EnforcementLevel.NOTIFY,
    EnforcementLevel.REDIRECT,
    EnforcementLevel.POWER_OFF,
)
TIME_UP = Block(BlockReason.OUTSIDE_WINDOW)
APP_BLOCKED = Block(BlockReason.APP_BLOCKED)


def plan(decision, level, caps=ALL, policy=None, **obs):  # type: ignore[no-untyped-def]
    return plan_actions(decision, level, caps, tv(**obs), policy or Policy(schedule=always_open()))


def test_allow_plans_nothing() -> None:
    assert plan(Allow(), OFF) == []


def test_warning_shows_message_when_supported() -> None:
    warn = Warn(5, LimitKind.BUDGET)
    assert plan(warn, NOTIFY) == [ShowMessage(MessageKind.TIME_WARNING, 5)]
    assert plan(warn, NOTIFY, caps={C.POWER_OFF}) == []


def test_notify_message_kind_follows_the_reason() -> None:
    assert plan(TIME_UP, NOTIFY) == [ShowMessage(MessageKind.TIME_UP)]
    assert plan(Block(BlockReason.OVERRIDE), NOTIFY) == [ShowMessage(MessageKind.TIME_UP)]
    assert plan(APP_BLOCKED, NOTIFY) == [ShowMessage(MessageKind.CONTENT_BLOCKED)]
    assert plan(TIME_UP, NOTIFY, caps={C.POWER_OFF}) == []


def test_power_off_needs_capability() -> None:
    assert plan(TIME_UP, OFF) == [PowerOff()]
    assert plan(TIME_UP, OFF, caps={C.GO_HOME}) == []


def test_time_limit_redirects_only_to_always_allowed_fallback() -> None:
    policy = Policy(fallback=ChannelTarget("news"), always_allowed_channels=frozenset({"news"}))
    assert plan(TIME_UP, REDIRECT, policy=policy) == [SetChannel("news")]
    not_exempt = Policy(fallback=ChannelTarget("news"))
    assert plan(TIME_UP, REDIRECT, policy=not_exempt) == []
    assert plan(TIME_UP, REDIRECT, caps={C.GO_HOME}, policy=policy) == []


def test_time_limit_never_redirects_home() -> None:
    assert plan(TIME_UP, REDIRECT, policy=Policy(fallback=HomeTarget())) == []


def test_fallback_target_kinds() -> None:
    app = Policy(fallback=AppTarget("kids"), always_allowed_apps=frozenset({"kids"}))
    inp = Policy(fallback=InputTarget("hdmi1"), always_allowed_inputs=frozenset({"hdmi1"}))
    assert plan(TIME_UP, REDIRECT, policy=app) == [LaunchApp("kids")]
    assert plan(TIME_UP, REDIRECT, policy=inp) == [SetInput("hdmi1")]


def test_blocked_content_prefers_fallback_then_home() -> None:
    fb = Policy(fallback=AppTarget("kids"), blocked_apps=frozenset({"games"}))
    assert plan(APP_BLOCKED, REDIRECT, policy=fb, foreground_app="games") == [LaunchApp("kids")]
    assert plan(APP_BLOCKED, REDIRECT, policy=Policy()) == [GoHome()]
    assert plan(APP_BLOCKED, REDIRECT, caps={C.POWER_OFF}) == []


def test_blocked_fallback_is_skipped_for_content_blocks() -> None:
    policy = Policy(fallback=AppTarget("games"), blocked_apps=frozenset({"games"}))
    assert plan(APP_BLOCKED, REDIRECT, policy=policy, foreground_app="games") == [GoHome()]
