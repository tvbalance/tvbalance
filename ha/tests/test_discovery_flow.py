import aiohttp
from custom_components.tvbalance.const import CONF_TOKEN, CONF_URL, DOMAIN
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.hassio import HassioServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .test_config_flow import INFO

HOST = "172.30.33.5"
URL = f"http://{HOST}:8765"
INFO_ADDON = HassioServiceInfo(
    config={"host": HOST, "port": 8765, "token": "tvb_addon"},
    name="TVBalance",
    slug="abc_tvbalance",
    uuid="d1",
)


async def _discover(hass: HomeAssistant, info: HassioServiceInfo = INFO_ADDON):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_HASSIO}, data=info
    )


async def test_discovery_asks_for_confirmation_then_creates_the_entry(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(f"{URL}/api/v1/info", json=INFO)
    aioclient_mock.get(f"{URL}/api/v1/tvs", json=[])
    result = await _discover(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "hassio_confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "TVBalance (Add-on)"
    assert result["data"] == {CONF_URL: URL, CONF_TOKEN: "tvb_addon"}


async def test_discovery_reports_an_unreachable_add_on(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(f"{URL}/api/v1/info", exc=aiohttp.ClientConnectionError)
    result = await _discover(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_discovery_reports_a_rejected_token(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(f"{URL}/api/v1/info", json=INFO)
    aioclient_mock.get(
        f"{URL}/api/v1/tvs",
        status=401,
        json={"error": {"code": "unauthenticated", "message": "no"}},
    )
    result = await _discover(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["errors"] == {"base": "invalid_auth"}


async def test_rediscovery_updates_the_token_of_the_existing_entry(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=URL, data={CONF_URL: URL, CONF_TOKEN: "tvb_old"}
    )
    entry.add_to_hass(hass)

    result = await _discover(hass)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_TOKEN] == "tvb_addon"


async def test_a_malformed_discovery_is_ignored(hass: HomeAssistant) -> None:
    broken = HassioServiceInfo(config={"host": HOST}, name="TVBalance", slug="s", uuid="d2")
    result = await _discover(hass, broken)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "invalid_discovery"
