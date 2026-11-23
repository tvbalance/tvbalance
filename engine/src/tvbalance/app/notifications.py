"""Web Push notifications for the events a parent needs to hear about."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import AsyncExitStack
from datetime import datetime, timedelta
from typing import Any, Protocol

from tvbalance.app.events import BusEvent, EventBus
from tvbalance.app.messages import _supported, messages_for
from tvbalance.infra.webpush import PushTarget, SendResult, VapidKeys
from tvbalance.ports.services import Clock
from tvbalance.ports.storage import PushSubscriptionRecord, SecretSettingsStore, Storage

log = logging.getLogger(__name__)

PUSH_EVENTS = frozenset(
    {"pairing_lost", "tv_unreachable", "blocked", "time_warning", "weekly_report"}
)
OPT_IN_EVENTS = frozenset({"weekly_report"})  # offered, but not on until the parent asks
VAPID_SECRET = "push_vapid_key"
MAX_FAILURES = 5
DEDUP_WINDOW = timedelta(minutes=10)
URGENT = frozenset({"pairing_lost", "blocked"})
TTL_WARNING = 300
TTL_DEFAULT = 12 * 3600
APP_NAME = "TVBalance"


class Sender(Protocol):
    async def send(
        self, target: PushTarget, payload: bytes, *, ttl: int = ..., urgency: str = ...
    ) -> SendResult: ...


async def load_vapid_keys(secrets: SecretSettingsStore) -> VapidKeys:
    """The Engine's VAPID key pair, created on first use. An unreadable one is replaced."""
    pem = await secrets.get(VAPID_SECRET)
    if pem:
        try:
            return VapidKeys.from_pem(pem)
        except ValueError:
            log.warning("the stored VAPID key is unusable; creating a new one")
    keys = VapidKeys.generate()
    await secrets.set(VAPID_SECRET, keys.to_pem())
    return keys


class PushNotifier:
    def __init__(self, storage: Storage, events: EventBus, sender: Sender, clock: Clock) -> None:
        self._storage = storage
        self._events = events
        self._sender = sender
        self._clock = clock
        self._recent: dict[tuple[str, str, str], datetime] = {}
        self._stack: AsyncExitStack | None = None
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stack = AsyncExitStack()
        queue = await self._stack.enter_async_context(self._events.subscribe())
        self._task = asyncio.create_task(self._consume(queue), name="push-notifier")

    async def stop(self) -> None:
        task, self._task = self._task, None
        stack, self._stack = self._stack, None
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        if stack is not None:
            await stack.aclose()

    async def _consume(self, queue: asyncio.Queue[BusEvent]) -> None:
        while True:
            event = await queue.get()
            try:
                await self.handle(event.tv_id, event.type, event.payload)
            except Exception:
                log.exception("could not send the %s notification", event.type)

    async def handle(self, tv_id: str | None, event_type: str, payload: dict[str, Any]) -> None:
        if tv_id is None or event_type not in PUSH_EVENTS:
            return
        reason = str(payload.get("reason", "")) if event_type == "blocked" else ""
        if self._is_repeat((tv_id, event_type, reason)):
            return
        subscriptions = [s for s in await self._storage.push.list() if event_type in s.events]
        if not subscriptions:
            return
        record = await self._storage.tvs.get(tv_id)
        title = record.name if record else APP_NAME
        path = f"#/tvs/{tv_id}/pair" if event_type == "pairing_lost" else f"#/tvs/{tv_id}"
        ttl = TTL_WARNING if event_type == "time_warning" else TTL_DEFAULT
        urgency = "high" if event_type in URGENT else "normal"
        await asyncio.gather(
            *(
                self._deliver(
                    sub,
                    {
                        "title": title,
                        "body": _body(event_type, payload, sub.language),
                        "tag": f"{event_type}:{tv_id}",
                        "url": _link(sub.app_url, path),
                    },
                    ttl,
                    urgency,
                )
                for sub in subscriptions
            )
        )

    async def send_test(self, subscription: PushSubscriptionRecord) -> SendResult:
        body = messages_for(_supported(subscription.language))["push_test"]
        payload = {
            "title": APP_NAME,
            "body": body,
            "tag": "test",
            "url": _link(subscription.app_url, "#/settings"),
        }
        return await self._deliver(subscription, payload, 600, "normal")

    def _is_repeat(self, key: tuple[str, str, str]) -> bool:
        now = self._clock.now()
        last = self._recent.get(key)
        if last is not None and now - last < DEDUP_WINDOW:
            return True
        self._recent = {k: t for k, t in self._recent.items() if now - t < DEDUP_WINDOW}
        self._recent[key] = now
        return False

    async def _deliver(
        self, sub: PushSubscriptionRecord, payload: dict[str, str], ttl: int, urgency: str
    ) -> SendResult:
        target = PushTarget(sub.endpoint, sub.p256dh, sub.auth)
        result = await self._sender.send(
            target, json.dumps(payload).encode(), ttl=ttl, urgency=urgency
        )
        push = self._storage.push
        if result is SendResult.DELIVERED:
            await push.record_delivery(sub.id)
        elif result is SendResult.GONE:
            await push.delete(sub.id)
        elif await push.record_failure(sub.id) >= MAX_FAILURES:
            log.warning("removing a push subscription after %d failures", MAX_FAILURES)
            await push.delete(sub.id)
        return result


def _link(app_url: str, path: str) -> str:
    return app_url.split("#")[0].rstrip("/") + "/" + path


def _body(event_type: str, payload: dict[str, Any], language: str) -> str:
    texts = messages_for(_supported(language))
    if event_type == "blocked":
        key = f"push_blocked_{payload.get('reason')}"
        return texts.get(key) or texts["push_blocked_override"]
    if event_type == "time_warning":
        minutes = int(payload.get("minutes_left") or 0)
        template = texts["push_time_warning_one" if minutes == 1 else "push_time_warning"]
        return template.format(minutes=minutes)
    if event_type == "weekly_report":
        total = int(payload.get("total_seconds") or 0) // 60
        duration = f"{total // 60} h {total % 60} min"
        return texts["push_weekly_report"].format(
            duration=duration, blocks=int(payload.get("blocks") or 0)
        )
    return texts[f"push_{event_type}"]
