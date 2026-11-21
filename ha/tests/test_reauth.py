from datetime import timedelta

from custom_components.tvbalance.const import CONF_TOKEN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .test_config_flow import URL
from .test_entities import make_tv, setup_engine

REFUSED = {"error": {"code": "unauthenticated", "message": "no"}}


async def test_a_refused_token_starts_reauth(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    entry = await setup_engine(hass, aioclient_mock, [make_tv()])
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{URL}/api/v1/tvs", status=401, json=REFUSED)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress_by_handler("tvbalance")
    assert [f["context"]["source"] for f in flows] == ["reauth"]
    assert entry.state is ConfigEntryState.LOADED


async def test_reauth_stores_the_new_token(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    entry = await setup_engine(hass, aioclient_mock, [make_tv()])
    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{URL}/api/v1/tvs", status=401, json=REFUSED)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: "wrong"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{URL}/api/v1/tvs", json=[])
    aioclient_mock.get(f"{URL}/api/v1/health", json={"status": "ok"})
    aioclient_mock.get(f"{URL}/api/v1/adapters", json=[])
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: " fresh "}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_TOKEN] == "fresh"

    await hass.async_block_till_done()
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
