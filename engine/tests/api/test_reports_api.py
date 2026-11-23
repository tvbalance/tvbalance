from collections.abc import Iterator
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from support import LICENSE_PUBLIC, T0, FakeClock, license_key, seed_tv, sign_in_as_admin

from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig
from tvbalance.domain.models import ContentKey
from tvbalance.sdk.fake import PLUGIN

URL = "/api/v1/reports/weekly"


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def client(engine_config: EngineConfig, clock: FakeClock) -> Iterator[TestClient]:
    app = create_app(
        plugins={"fake": PLUGIN},
        include_testing=True,
        config=engine_config,
        clock=clock,
        license_public_keys=(LICENSE_PUBLIC,),
    )
    with TestClient(app) as running:
        sign_in_as_admin(running)
        yield running


def test_the_report_needs_pro(client: TestClient) -> None:
    response = client.get(URL)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "requires_pro"


def test_the_report_lists_each_tv_for_the_week(client: TestClient) -> None:
    tv_id = seed_tv(client)
    assert client.put("/api/v1/license", json={"key": license_key()}).status_code == 200
    assert client.portal is not None
    storage = client.app.state.storage  # type: ignore[attr-defined]
    monday = date(2026, 11, 9)  # the week before the one that holds T0 (Tuesday 17 November)
    client.portal.call(storage.usage.add_watched, tv_id, monday + timedelta(days=1), 1200)
    client.portal.call(
        storage.content_usage.add, tv_id, monday + timedelta(days=1), ContentKey("app", "tv"), 900
    )
    body = client.get(URL).json()
    assert (body["first"], body["last"]) == (monday.isoformat(), "2026-11-15")
    (tv,) = body["tvs"]
    assert tv["tv_id"] == tv_id and tv["total_seconds"] == 1200 and len(tv["days"]) == 7
    assert tv["top_content"] == [{"kind": "app", "id": "tv", "seconds": 900}]
    chosen = client.get(URL, params={"week": T0.date().isoformat()}).json()
    assert chosen["first"] == "2026-11-16"
    assert client.get(URL, params={"week": "not-a-date"}).status_code == 422
