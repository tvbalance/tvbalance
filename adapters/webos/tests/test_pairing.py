import asyncio
from collections.abc import AsyncIterator

import pytest
from aiowebostv import webos_client

from tvbalance.sdk.types import PairingState
from tvbalance_adapter_webos import pairing
from tvbalance_adapter_webos.pairing import WebOsPairing
from tvbalance_adapter_webos.testing import SimulatedWebOsTV


@pytest.fixture
async def tv() -> AsyncIterator[SimulatedWebOsTV]:
    sim = SimulatedWebOsTV()
    await sim.start()
    yield sim
    await sim.stop()


async def _finish(flow: WebOsPairing) -> PairingState:
    state = PairingState.WAITING_FOR_USER
    for _ in range(40):
        state = await flow.poll()
        if state is not PairingState.WAITING_FOR_USER:
            break
    return state


async def test_accepting_the_prompt_completes_with_a_key(tv: SimulatedWebOsTV) -> None:
    flow = WebOsPairing(tv.host)
    assert await flow.start() is PairingState.WAITING_FOR_USER
    assert await _finish(flow) is PairingState.COMPLETED
    assert flow.credentials() == {"client_key": tv.client_key}


async def test_rejecting_the_prompt_fails(tv: SimulatedWebOsTV) -> None:
    tv.pairing_prompt = "reject"
    flow = WebOsPairing(tv.host)
    await flow.start()
    assert await _finish(flow) is PairingState.FAILED
    assert flow.credentials() == {}


async def test_waits_while_the_user_has_not_answered(tv: SimulatedWebOsTV) -> None:
    tv.pairing_prompt = "hold"
    flow = WebOsPairing(tv.host)
    await flow.start()
    assert await flow.poll() is PairingState.WAITING_FOR_USER
    tv.answer_prompt(True)
    assert await _finish(flow) is PairingState.COMPLETED


async def test_a_prompt_the_library_gave_up_on_is_shown_again(
    tv: SimulatedWebOsTV, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(webos_client, "RECEIVE_TIMEOUT", 0.2)
    monkeypatch.setattr(pairing, "MAX_ATTEMPTS", 50)
    tv.pairing_prompt = "hold"
    flow = WebOsPairing(tv.host)
    await flow.start()
    await asyncio.sleep(0.5)  # the first attempt timed out and a second prompt was sent
    assert len(tv.registered_keys) >= 2
    assert await flow.poll() is PairingState.WAITING_FOR_USER
    tv.answer_prompt(True)
    assert await _finish(flow) is PairingState.COMPLETED


async def test_unreachable_tv_fails() -> None:
    flow = WebOsPairing("203.0.113.1.invalid")
    await flow.start()
    assert await _finish(flow) is PairingState.FAILED


async def test_cancel_stops_the_attempt(tv: SimulatedWebOsTV) -> None:
    tv.pairing_prompt = "hold"
    flow = WebOsPairing(tv.host)
    await flow.start()
    await flow.cancel()
    assert await flow.poll() is PairingState.FAILED
