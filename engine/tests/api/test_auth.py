from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from support import ADMIN_PASSWORD, CSRF_HEADER, FakeClock, sign_in_as_admin

from tvbalance.api.app import create_app
from tvbalance.config import EngineConfig

SUPERVISOR = "172.30.32.2"


@contextmanager
def running(
    config: EngineConfig, *, trusted: frozenset[str] = frozenset(), peer: str = "testclient"
) -> Iterator[TestClient]:
    app = create_app(plugins={}, config=replace(config, ingress_trusted=trusted))
    with TestClient(app, client=(peer, 50000)) as client:
        yield client


def error(response: Any) -> dict[str, Any]:
    body: dict[str, Any] = response.json()["error"]
    return body


def sign_out_locally(client: TestClient) -> None:
    client.cookies.clear()
    client.headers.pop(CSRF_HEADER, None)


def log_in(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"password": ADMIN_PASSWORD})
    assert response.status_code == 200, response.text
    client.headers[CSRF_HEADER] = response.json()["csrf_token"]


def create_token(client: TestClient, scopes: list[str], name: str = "Home Assistant") -> str:
    response = client.post("/api/v1/auth/tokens", json={"name": name, "scopes": scopes})
    assert response.status_code == 201, response.text
    token: str = response.json()["token"]
    return token


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- first run -----------------------------------------------------------------------------------


def test_setup_is_offered_until_the_admin_exists(app_client: TestClient) -> None:
    assert app_client.get("/api/v1/auth/state").json() == {"setup_required": True}
    sign_in_as_admin(app_client)
    assert app_client.get("/api/v1/auth/state").json() == {"setup_required": False}


def test_before_setup_other_routes_point_to_the_setup(app_client: TestClient) -> None:
    denied = app_client.get("/api/v1/auth/me")
    assert denied.status_code == 401 and error(denied)["code"] == "setup_required"
    login = app_client.post("/api/v1/auth/login", json={"password": ADMIN_PASSWORD})
    assert login.status_code == 409 and error(login)["code"] == "setup_required"


def test_setup_signs_in_with_safe_cookies_and_works_only_once(app_client: TestClient) -> None:
    response = app_client.post("/api/v1/auth/setup", json={"password": ADMIN_PASSWORD})
    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "admin" and body["full_admin"] is True
    assert set(body["scopes"]) == {"read", "control", "admin"}
    assert body["csrf_token"]

    cookies = {c.split("=")[0]: c.lower() for c in response.headers.get_list("set-cookie")}
    session = cookies["tvb_session"]
    assert "httponly" in session and "samesite=strict" in session and "secure" not in session
    assert "httponly" not in cookies["tvb_csrf"]  # the UI must be able to read it

    again = app_client.post("/api/v1/auth/setup", json={"password": "another long password"})
    assert again.status_code == 409 and error(again)["code"] == "conflict"


def test_a_weak_password_is_refused(app_client: TestClient) -> None:
    response = app_client.post("/api/v1/auth/setup", json={"password": "short"})
    assert response.status_code == 422 and error(response)["code"] == "validation_failed"
    assert app_client.get("/api/v1/auth/state").json() == {"setup_required": True}


def test_secure_cookies_are_used_over_https(app_client: TestClient) -> None:
    response = app_client.post(
        "/api/v1/auth/setup",
        json={"password": ADMIN_PASSWORD},
        headers={"X-Forwarded-Proto": "https"},
    )
    assert all("secure" in c.lower() for c in response.headers.get_list("set-cookie"))


# --- sessions ------------------------------------------------------------------------------------


def test_me_needs_a_sign_in(admin_client: TestClient) -> None:
    me = admin_client.get("/api/v1/auth/me")
    assert me.status_code == 200 and me.json()["kind"] == "admin"
    sign_out_locally(admin_client)
    denied = admin_client.get("/api/v1/auth/me")
    assert denied.status_code == 401 and error(denied)["code"] == "not_authenticated"


def test_a_cookie_write_needs_the_csrf_header(admin_client: TestClient) -> None:
    token = admin_client.headers.pop(CSRF_HEADER)
    missing = admin_client.post("/api/v1/auth/logout")
    assert missing.status_code == 403 and error(missing)["code"] == "forbidden"
    wrong = admin_client.post("/api/v1/auth/logout", headers={CSRF_HEADER: "0" * 32})
    assert wrong.status_code == 403
    assert admin_client.get("/api/v1/auth/me").status_code == 200  # reads need no header
    assert admin_client.post("/api/v1/auth/logout", headers={CSRF_HEADER: token}).status_code == 204


def test_logout_ends_the_session(admin_client: TestClient) -> None:
    assert admin_client.post("/api/v1/auth/logout").status_code == 204
    assert admin_client.get("/api/v1/auth/me").status_code == 401


def test_login_with_the_right_and_the_wrong_password(admin_client: TestClient) -> None:
    sign_out_locally(admin_client)
    wrong = admin_client.post("/api/v1/auth/login", json={"password": "not the password"})
    assert wrong.status_code == 401 and error(wrong)["code"] == "not_authenticated"
    right = admin_client.post("/api/v1/auth/login", json={"password": ADMIN_PASSWORD})
    assert right.status_code == 200 and right.json()["csrf_token"]
    assert admin_client.get("/api/v1/auth/me").status_code == 200


def test_repeated_wrong_passwords_are_slowed_down(admin_client: TestClient) -> None:
    sign_out_locally(admin_client)
    for _ in range(4):
        admin_client.post("/api/v1/auth/login", json={"password": "not the password"})
    limited = admin_client.post("/api/v1/auth/login", json={"password": ADMIN_PASSWORD})
    assert limited.status_code == 429 and error(limited)["code"] == "rate_limited"
    assert int(limited.headers["Retry-After"]) >= 1


def test_a_stale_cookie_is_just_not_signed_in(admin_client: TestClient) -> None:
    admin_client.cookies.set("tvb_session", "forged")
    assert admin_client.get("/api/v1/auth/me").status_code == 401


def test_sessions_are_listed_and_the_others_can_be_ended(admin_client: TestClient) -> None:
    first_cookies = dict(admin_client.cookies)
    log_in(admin_client)  # a second session
    sessions = admin_client.get("/api/v1/auth/sessions").json()
    assert len(sessions) == 2
    assert sum(s["current"] for s in sessions) == 1

    assert admin_client.delete("/api/v1/auth/sessions").json() == {"revoked": 1}
    assert len(admin_client.get("/api/v1/auth/sessions").json()) == 1
    admin_client.cookies.clear()
    for name, value in first_cookies.items():
        admin_client.cookies.set(name, value)
    assert admin_client.get("/api/v1/auth/me").status_code == 401  # the first session was ended


def test_one_session_can_be_revoked_by_id(admin_client: TestClient) -> None:
    [session] = admin_client.get("/api/v1/auth/sessions").json()
    assert admin_client.delete(f"/api/v1/auth/sessions/{session['id']}").status_code == 204
    assert admin_client.get("/api/v1/auth/me").status_code == 401
    sign_out_locally(admin_client)
    log_in(admin_client)
    missing = admin_client.delete("/api/v1/auth/sessions/nope")
    assert missing.status_code == 404 and error(missing)["code"] == "not_found"


def test_changing_the_password(admin_client: TestClient) -> None:
    body = {"current_password": "not the password", "new_password": "a brand new password"}
    assert admin_client.put("/api/v1/auth/password", json=body).status_code == 401
    body["current_password"] = ADMIN_PASSWORD
    assert admin_client.put("/api/v1/auth/password", json=body).status_code == 204
    assert admin_client.get("/api/v1/auth/me").status_code == 200  # this session stays
    sign_out_locally(admin_client)
    old = admin_client.post("/api/v1/auth/login", json={"password": ADMIN_PASSWORD})
    assert old.status_code == 401
    new = admin_client.post("/api/v1/auth/login", json={"password": "a brand new password"})
    assert new.status_code == 200


# --- PIN -----------------------------------------------------------------------------------------


def test_pin_login_gives_a_session_that_cannot_manage_access(admin_client: TestClient) -> None:
    assert admin_client.put("/api/v1/auth/pin", json={"pin": "4821"}).status_code == 204
    sign_out_locally(admin_client)

    wrong = admin_client.post("/api/v1/auth/pin-login", json={"pin": "0000"})
    assert wrong.status_code == 401
    unlocked = admin_client.post("/api/v1/auth/pin-login", json={"pin": "4821"})
    assert unlocked.status_code == 200
    body = unlocked.json()
    assert body["kind"] == "pin" and body["full_admin"] is False
    assert set(body["scopes"]) == {"read", "control"}
    admin_client.headers[CSRF_HEADER] = body["csrf_token"]

    assert admin_client.get("/api/v1/adapters").status_code == 200
    for denied in (
        admin_client.put("/api/v1/auth/pin", json={"pin": "1111"}),
        admin_client.get("/api/v1/auth/tokens"),
        admin_client.get("/api/v1/auth/sessions"),
        admin_client.put(
            "/api/v1/auth/password",
            json={"current_password": ADMIN_PASSWORD, "new_password": "a brand new password"},
        ),
    ):
        assert denied.status_code == 403 and error(denied)["code"] == "forbidden"


def test_a_bad_pin_is_refused_and_the_pin_can_be_removed(admin_client: TestClient) -> None:
    bad = admin_client.put("/api/v1/auth/pin", json={"pin": "12"})
    assert bad.status_code == 422
    admin_client.put("/api/v1/auth/pin", json={"pin": "4821"})
    assert admin_client.delete("/api/v1/auth/pin").status_code == 204
    sign_out_locally(admin_client)
    assert admin_client.post("/api/v1/auth/pin-login", json={"pin": "4821"}).status_code == 401


def test_five_wrong_pins_lock_it_until_the_password_is_used(engine_config: EngineConfig) -> None:
    clock = FakeClock()
    app = create_app(plugins={}, config=engine_config, clock=clock)
    with TestClient(app) as client:
        sign_in_as_admin(client)
        client.put("/api/v1/auth/pin", json={"pin": "4821"})
        sign_out_locally(client)
        for _ in range(5):
            client.post("/api/v1/auth/pin-login", json={"pin": "0000"})
            clock.advance(seconds=1000)  # past the rate limiter, so only the lock is left
        locked = client.post("/api/v1/auth/pin-login", json={"pin": "4821"})
        assert locked.status_code == 403 and error(locked)["code"] == "pin_locked"
        log_in(client)
        sign_out_locally(client)
        assert client.post("/api/v1/auth/pin-login", json={"pin": "4821"}).status_code == 200


# --- API tokens ----------------------------------------------------------------------------------


def test_a_token_authenticates_without_a_cookie_or_csrf(admin_client: TestClient) -> None:
    token = create_token(admin_client, ["read", "control"])
    sign_out_locally(admin_client)
    assert admin_client.get("/api/v1/adapters").status_code == 401
    assert admin_client.get("/api/v1/adapters", headers=bearer(token)).status_code == 200
    me = admin_client.get("/api/v1/auth/me", headers=bearer(token)).json()
    assert me["kind"] == "token" and me["name"] == "Home Assistant"
    assert set(me["scopes"]) == {"read", "control"}
    assert me["full_admin"] is False and me["csrf_token"] is None
    # a write by token needs no CSRF header
    assert admin_client.post("/api/v1/auth/logout", headers=bearer(token)).status_code == 204


def test_a_token_cannot_manage_access(admin_client: TestClient) -> None:
    token = create_token(admin_client, ["read", "control", "admin"])
    sign_out_locally(admin_client)
    for path in ("/api/v1/auth/tokens", "/api/v1/auth/sessions"):
        denied = admin_client.get(path, headers=bearer(token))
        assert denied.status_code == 403
    made = admin_client.post(
        "/api/v1/auth/tokens",
        headers=bearer(token),
        json={"name": "sneaky", "scopes": ["admin"]},
    )
    assert made.status_code == 403


def test_a_token_needs_the_scope_of_the_route(admin_client: TestClient) -> None:
    token = create_token(admin_client, ["control"])
    sign_out_locally(admin_client)
    denied = admin_client.get("/api/v1/adapters", headers=bearer(token))
    assert denied.status_code == 403 and "'read'" in error(denied)["message"]


def test_the_token_is_shown_once_and_never_listed(admin_client: TestClient) -> None:
    token = create_token(admin_client, ["read"])
    listed = admin_client.get("/api/v1/auth/tokens")
    assert listed.status_code == 200
    assert token not in listed.text
    [entry] = listed.json()
    assert entry["name"] == "Home Assistant" and entry["scopes"] == ["read"]
    assert entry["last_used_at"] is None and entry["revoked_at"] is None


def test_a_revoked_token_stops_working(admin_client: TestClient) -> None:
    token = create_token(admin_client, ["read"])
    [entry] = admin_client.get("/api/v1/auth/tokens").json()
    assert admin_client.delete(f"/api/v1/auth/tokens/{entry['id']}").status_code == 204
    assert admin_client.delete(f"/api/v1/auth/tokens/{entry['id']}").status_code == 404
    sign_out_locally(admin_client)
    denied = admin_client.get("/api/v1/adapters", headers=bearer(token))
    assert denied.status_code == 401 and error(denied)["code"] == "not_authenticated"


def test_a_wrong_token_is_an_error_even_with_a_valid_session(admin_client: TestClient) -> None:
    denied = admin_client.get("/api/v1/adapters", headers=bearer("tvb_not-a-real-token"))
    assert denied.status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {"name": "HA", "scopes": []},
        {"name": "HA", "scopes": ["root"]},
        {"name": " ", "scopes": ["read"]},
        {"scopes": ["read"]},
        {"name": "HA", "scopes": ["read"], "extra": 1},
    ],
)
def test_token_requests_are_validated(admin_client: TestClient, body: dict[str, Any]) -> None:
    response = admin_client.post("/api/v1/auth/tokens", json=body)
    assert response.status_code == 422 and error(response)["code"] == "validation_failed"


# --- Home Assistant Ingress ----------------------------------------------------------------------


def test_the_supervisor_vouches_for_the_home_assistant_user(engine_config: EngineConfig) -> None:
    with running(engine_config, trusted=frozenset({SUPERVISOR}), peer=SUPERVISOR) as client:
        me = client.get(
            "/api/v1/auth/me",
            headers={"X-Remote-User-Id": "abc123", "X-Remote-User-Name": "Anna"},
        )
        assert me.status_code == 200
        assert me.json()["kind"] == "ingress" and me.json()["name"] == "Anna"
        assert me.json()["full_admin"] is True
        # no admin account is needed, and writes need no CSRF header
        assert (
            client.put("/api/v1/auth/pin", json={"pin": "4821"}, headers=_ha()).status_code == 204
        )
        no_headers = client.get("/api/v1/auth/me")
        assert no_headers.status_code == 401


def _ha() -> dict[str, str]:
    return {"X-Remote-User-Id": "abc123"}


def test_ingress_headers_from_anyone_else_are_ignored(engine_config: EngineConfig) -> None:
    with running(engine_config, trusted=frozenset({SUPERVISOR}), peer="203.0.113.50") as client:
        assert client.get("/api/v1/auth/me", headers=_ha()).status_code == 401
    with running(engine_config, peer=SUPERVISOR) as client:  # nobody is trusted by default
        assert client.get("/api/v1/auth/me", headers=_ha()).status_code == 401


# --- the envelope --------------------------------------------------------------------------------


def test_errors_share_one_envelope(admin_client: TestClient) -> None:
    unknown = admin_client.get("/api/v1/nope")
    assert unknown.status_code == 404 and error(unknown)["code"] == "not_found"
    wrong_method = admin_client.put("/api/v1/health")
    assert wrong_method.status_code == 405 and error(wrong_method)["code"] == "method_not_allowed"


def test_validation_errors_say_where(admin_client: TestClient) -> None:
    response = admin_client.post("/api/v1/auth/tokens", json={"name": 5})
    body = error(response)
    assert response.status_code == 422 and body["code"] == "validation_failed"
    assert {tuple(d["loc"]) for d in body["details"]} >= {("body", "name"), ("body", "scopes")}
    assert "input" not in body["details"][0]  # what the caller typed is not echoed back


def test_expired_admin_sessions_stop_working(engine_config: EngineConfig) -> None:
    clock = FakeClock()
    app = create_app(plugins={}, config=engine_config, clock=clock)
    with TestClient(app) as client:
        sign_in_as_admin(client)
        assert client.get("/api/v1/auth/me").status_code == 200
        clock.advance(days=31)
        assert client.get("/api/v1/auth/me").status_code == 401
