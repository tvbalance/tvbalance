"""HTTPS with the Engine's local CA: the user confirms the fingerprint once, then it is pinned."""

import ssl
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp
from aiohttp.client_reqrep import ConnectionKey
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from custom_components.tvbalance.const import CONF_CA_PEM, CONF_TOKEN, CONF_URL, DOMAIN
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from tvbalance_client import ca_fingerprint

from .test_config_flow import ADAPTERS, INFO

URL = "https://engine.local:8766"
CA_URL = f"{URL}/api/v1/tls/ca.crt"


def make_ca(name: str = "TVBalance Local CA") -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(hours=1))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def untrusted() -> aiohttp.ClientConnectorCertificateError:
    key = ConnectionKey("engine.local", 8766, True, None, None, None, None)
    return aiohttp.ClientConnectorCertificateError(key, ssl.SSLCertVerificationError("unknown CA"))


def engine_answers(mock: AiohttpClientMocker, tvs: list[Any] | None = None) -> None:
    mock.get(f"{URL}/api/v1/info", json=INFO)
    mock.get(f"{URL}/api/v1/tvs", json=tvs or [])
    mock.get(f"{URL}/api/v1/health", json={"status": "ok"})
    mock.get(f"{URL}/api/v1/adapters", json=ADAPTERS)


async def _start(hass: HomeAssistant, token: str = "secret"):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: URL, CONF_TOKEN: token}
    )


async def test_an_unknown_ca_asks_for_the_fingerprint_then_pins_it(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    pem = make_ca()
    aioclient_mock.get(f"{URL}/api/v1/info", exc=untrusted())
    aioclient_mock.get(CA_URL, text=pem)
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "tls_confirm"
    assert result["description_placeholders"] == {"url": URL, "fingerprint": ca_fingerprint(pem)}

    aioclient_mock.clear_requests()
    engine_answers(aioclient_mock)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_URL: URL, CONF_TOKEN: "secret", CONF_CA_PEM: pem}


async def test_a_certificate_without_a_local_ca_is_reported(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.get(f"{URL}/api/v1/info", exc=untrusted())
    aioclient_mock.get(CA_URL, status=404)
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"
    assert result["errors"] == {"base": "untrusted_certificate"}


async def test_a_trusted_certificate_needs_no_pinning(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    engine_answers(aioclient_mock)
    result = await _start(hass)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert CONF_CA_PEM not in result["data"]


async def test_a_changed_ca_is_confirmed_again_through_reauth(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    old, new = make_ca(), make_ca()
    engine_answers(aioclient_mock)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=URL,
        data={CONF_URL: URL, CONF_TOKEN: "secret", CONF_CA_PEM: old},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    # The Engine created a new CA: the pinned one no longer verifies its certificate.
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{URL}/api/v1/health", exc=untrusted())
    aioclient_mock.get(f"{URL}/api/v1/tvs", exc=untrusted())
    aioclient_mock.get(CA_URL, text=new)
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [f["context"]["source"] for f in flows] == ["reauth"]

    result = flows[0]
    assert result["step_id"] == "tls_confirm"
    form = await hass.config_entries.flow.async_configure(result["flow_id"], None)
    assert form["description_placeholders"]["fingerprint"] == ca_fingerprint(new)

    aioclient_mock.clear_requests()
    engine_answers(aioclient_mock)
    done = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert done["type"] is FlowResultType.ABORT and done["reason"] == "reauth_successful"
    assert entry.data[CONF_CA_PEM] == new

    await hass.async_block_till_done()
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
