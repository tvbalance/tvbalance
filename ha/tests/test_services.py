from typing import Any

import aiohttp
import pytest
from custom_components.tvbalance.const import DOMAIN
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError, Unauthorized
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockUser
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .test_config_flow import URL
from .test_entities import make_tv, setup_engine, state_of

OVERRIDE = {
    "allow": False,
    "until": "2026-01-01T10:00:00+00:00",
    "created_at": "2026-01-01T09:00:00+00:00",
}
TV = f"{URL}/api/v1/tvs/tv1"


@pytest.fixture
async def device_id(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> str:
    await setup_engine(hass, aioclient_mock, [make_tv()])
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "tv1")})
    assert device
    aioclient_mock.post(f"{TV}/bonus", json={"day": "2026-01-01", "bonus_minutes": 15})
    aioclient_mock.post(f"{TV}/override", json=OVERRIDE)
    aioclient_mock.post(f"{TV}/pause", json=OVERRIDE)
    aioclient_mock.delete(f"{TV}/override", status=204)
    aioclient_mock.patch(TV, json=make_tv(enabled=False))
    return device.id


def writes(aioclient_mock: AiohttpClientMocker) -> list[tuple[str, str, Any]]:
    return [(m, str(u), d) for m, u, d, _ in aioclient_mock.mock_calls if m != "GET"]


@pytest.mark.parametrize(
    ("service", "data", "method", "path", "body"),
    [
        ("bonus", {"minutes": 15}, "POST", "/bonus", {"minutes": 15}),
        (
            "allow",
            {"minutes": 60},
            "POST",
            "/override",
            {"allow": True, "until_midnight": False, "minutes": 60},
        ),
        (
            "block",
            {"until_midnight": True},
            "POST",
            "/override",
            {"allow": False, "until_midnight": True},
        ),
        ("pause", {}, "POST", "/pause", {"minutes": 30}),
        ("pause", {"minutes": 10}, "POST", "/pause", {"minutes": 10}),
        ("clear_override", {}, "DELETE", "/override", None),
        ("set_monitoring", {"enabled": False}, "PATCH", "", {"enabled": False}),
    ],
)
async def test_each_service_calls_the_engine(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    device_id: str,
    service: str,
    data: dict[str, Any],
    method: str,
    path: str,
    body: Any,
) -> None:
    # No user in the context: this is how automations and blueprints call.
    await hass.services.async_call(DOMAIN, service, {"device_id": device_id, **data}, blocking=True)
    assert writes(aioclient_mock) == [(method, f"{TV}{path}", body)]


@pytest.mark.parametrize("data", [{}, {"minutes": 5, "until_midnight": True}])
async def test_allow_and_block_need_exactly_one_duration(
    hass: HomeAssistant, device_id: str, data: dict[str, Any]
) -> None:
    for service in ("allow", "block"):
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN, service, {"device_id": device_id, **data}, blocking=True
            )


async def test_a_user_who_is_not_an_administrator_is_refused(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, device_id: str
) -> None:
    child = MockUser(name="child").add_to_hass(hass)
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN,
            "bonus",
            {"device_id": device_id, "minutes": 30},
            blocking=True,
            context=Context(user_id=child.id),
        )
    assert writes(aioclient_mock) == []


async def test_an_administrator_is_allowed(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, device_id: str
) -> None:
    parent = MockUser(name="parent", is_owner=True).add_to_hass(hass)
    await hass.services.async_call(
        DOMAIN,
        "bonus",
        {"device_id": device_id, "minutes": 30},
        blocking=True,
        context=Context(user_id=parent.id),
    )
    assert writes(aioclient_mock) == [("POST", f"{TV}/bonus", {"minutes": 30})]


async def test_an_unknown_device_is_refused(hass: HomeAssistant, device_id: str) -> None:
    with pytest.raises(ServiceValidationError) as refused:
        await hass.services.async_call(
            DOMAIN, "bonus", {"device_id": "nope", "minutes": 5}, blocking=True
        )
    assert refused.value.translation_key == "unknown_device"


async def test_a_token_without_the_scope_gets_a_translated_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, device_id: str
) -> None:
    aioclient_mock.clear_requests()  # the first matching mock wins
    aioclient_mock.patch(
        TV, status=403, json={"error": {"code": "forbidden", "message": "scope admin required"}}
    )
    with pytest.raises(HomeAssistantError) as refused:
        await hass.services.async_call(
            DOMAIN, "set_monitoring", {"device_id": device_id, "enabled": True}, blocking=True
        )
    assert refused.value.translation_key == "not_allowed"
    assert "scope admin required" in str(refused.value.translation_placeholders)


async def test_an_unreachable_engine_gets_a_translated_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, device_id: str
) -> None:
    aioclient_mock.clear_requests()
    aioclient_mock.post(f"{TV}/bonus", exc=aiohttp.ClientConnectionError)
    with pytest.raises(HomeAssistantError) as refused:
        await hass.services.async_call(
            DOMAIN, "bonus", {"device_id": device_id, "minutes": 5}, blocking=True
        )
    assert refused.value.translation_key == "engine_error"


async def test_the_pause_button_pauses_for_half_an_hour(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, device_id: str
) -> None:
    button = state_of(hass, "button", "pause")
    await hass.services.async_call(
        "button", "press", {"entity_id": button.entity_id}, blocking=True
    )
    assert writes(aioclient_mock) == [("POST", f"{TV}/pause", {"minutes": 30})]


async def test_the_pause_button_reports_a_refusal(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, device_id: str
) -> None:
    aioclient_mock.clear_requests()
    aioclient_mock.post(
        f"{TV}/pause", status=403, json={"error": {"code": "forbidden", "message": "no"}}
    )
    button = state_of(hass, "button", "pause")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "button", "press", {"entity_id": button.entity_id}, blocking=True
        )
