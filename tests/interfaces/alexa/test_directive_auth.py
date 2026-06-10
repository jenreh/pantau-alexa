"""Tests: bearer-token validation on POST /alexa/directive.

Uses the real JwtService so we verify the full validation path.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tests.interfaces.alexa.conftest import DEVICES_YAML, directive, discovery_directive

from pantau.adapters.auth_code_store import AuthCodeStore
from pantau.adapters.jwt_service import JwtService
from pantau.adapters.sqlite_user_store import SqliteUserStore
from pantau.api.app import create_app
from pantau.composition import build_oauth_test_container
from pantau.config.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        jwt_secret=SecretStr("auth-test-secret-0123456789abcdef"),
        jwt_access_token_expire_minutes=60,
    )


@pytest.fixture
def jwt_service(settings: Settings) -> JwtService:
    return JwtService(
        settings.jwt_secret.get_secret_value(),
        access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
    )


@pytest.fixture
async def auth_client(
    tmp_path: Path, settings: Settings, jwt_service: JwtService
) -> AsyncGenerator[TestClient]:
    """App wired with real JwtService for the directive endpoint."""
    cfg = tmp_path / "devices.yaml"
    cfg.write_text(DEVICES_YAML, encoding="utf-8")

    store = SqliteUserStore(tmp_path / "test.db")
    await store.start()
    auth_codes = AuthCodeStore()

    container = build_oauth_test_container(cfg, store, jwt_service, auth_codes)
    app = create_app(settings=settings, container=container)
    client = TestClient(app)
    yield client
    await store.stop()


class TestDirectiveBearerValidation:
    def test_valid_token_allows_directive(
        self, auth_client: TestClient, jwt_service: JwtService
    ) -> None:
        token, _ = jwt_service.issue_access_token("user-1")
        resp = auth_client.post(
            "/alexa/directive",
            json=directive(
                "Alexa.PowerController", "TurnOn", endpoint_id="zdf", bearer_token=token
            ),
        )
        assert resp.status_code == 200

    def test_missing_token_returns_401(self, auth_client: TestClient) -> None:
        body = {
            "directive": {
                "header": {
                    "namespace": "Alexa.PowerController",
                    "name": "TurnOn",
                    "messageId": "msg-1",
                    "payloadVersion": "3",
                },
                "endpoint": {
                    "endpointId": "zdf",
                    "cookie": {},
                },
                "payload": {},
            }
        }
        resp = auth_client.post("/alexa/directive", json=body)
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, auth_client: TestClient) -> None:
        resp = auth_client.post(
            "/alexa/directive",
            json=directive(
                "Alexa.PowerController",
                "TurnOn",
                endpoint_id="zdf",
                bearer_token="invalid-token",
            ),
        )
        assert resp.status_code == 401

    def test_discovery_directive_with_valid_token(
        self, auth_client: TestClient, jwt_service: JwtService
    ) -> None:
        token, _ = jwt_service.issue_access_token("user-1")
        resp = auth_client.post(
            "/alexa/directive", json=discovery_directive(bearer_token=token)
        )
        assert resp.status_code == 200

    def test_discovery_directive_with_invalid_token_returns_401(
        self, auth_client: TestClient
    ) -> None:
        resp = auth_client.post(
            "/alexa/directive", json=discovery_directive(bearer_token="bad-token")
        )
        assert resp.status_code == 401

    def test_token_with_wrong_scope_returns_403(
        self, auth_client: TestClient, settings: Settings
    ) -> None:
        from jose import jwt as _jwt

        token = _jwt.encode(
            {"sub": "user-1", "scope": "other", "exp": 2_000_000_000},
            settings.jwt_secret.get_secret_value(),
            algorithm="HS256",
        )
        resp = auth_client.post(
            "/alexa/directive",
            json=directive(
                "Alexa.PowerController", "TurnOn", endpoint_id="zdf", bearer_token=token
            ),
        )
        assert resp.status_code == 403


HMAC_SECRET = "hmac-shared-secret-0123456789abcdef"  # noqa: S105


def _jwt_service_for(settings: Settings) -> JwtService:
    return JwtService(
        settings.jwt_secret.get_secret_value(),
        access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
    )


def _sign(body: bytes, timestamp: int, secret: str = HMAC_SECRET) -> str:
    import hashlib
    import hmac as _hmac

    return _hmac.new(
        secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()


class TestDirectiveHmacVerification:
    """When shared_secret is configured, /alexa/directive requires a valid HMAC."""

    @pytest.fixture
    def hmac_settings(self) -> Settings:
        return Settings(
            jwt_secret=SecretStr("auth-test-secret-0123456789abcdef"),
            shared_secret=SecretStr(HMAC_SECRET),
            jwt_access_token_expire_minutes=60,
        )

    @pytest.fixture
    async def hmac_client(
        self, tmp_path: Path, hmac_settings: Settings
    ) -> AsyncGenerator[TestClient]:
        cfg = tmp_path / "devices.yaml"
        cfg.write_text(DEVICES_YAML, encoding="utf-8")
        store = SqliteUserStore(tmp_path / "test.db")
        await store.start()
        container = build_oauth_test_container(
            cfg, store, _jwt_service_for(hmac_settings), AuthCodeStore()
        )
        app = create_app(settings=hmac_settings, container=container)
        yield TestClient(app)
        await store.stop()

    def _post(
        self,
        client: TestClient,
        body: dict,
        *,
        timestamp: int | None = None,
        signature: str | None = None,
    ):
        import json as _json
        import time as _time

        raw = _json.dumps(body).encode()
        ts = timestamp if timestamp is not None else int(_time.time())
        sig = signature if signature is not None else _sign(raw, ts)
        return client.post(
            "/alexa/directive",
            content=raw,
            headers={
                "Content-Type": "application/json",
                "X-Pantau-Timestamp": str(ts),
                "X-Pantau-Signature": sig,
            },
        )

    def test_valid_hmac_and_token_allows_directive(
        self, hmac_client: TestClient, hmac_settings: Settings
    ) -> None:
        token, _ = _jwt_service_for(hmac_settings).issue_access_token("user-1")
        body = directive(
            "Alexa.PowerController", "TurnOn", endpoint_id="zdf", bearer_token=token
        )
        assert self._post(hmac_client, body).status_code == 200

    def test_missing_hmac_headers_returns_401(self, hmac_client: TestClient) -> None:
        body = directive("Alexa.PowerController", "TurnOn", endpoint_id="zdf")
        resp = hmac_client.post("/alexa/directive", json=body)
        assert resp.status_code == 401

    def test_wrong_signature_returns_401(self, hmac_client: TestClient) -> None:
        body = directive("Alexa.PowerController", "TurnOn", endpoint_id="zdf")
        resp = self._post(hmac_client, body, signature="0" * 64)
        assert resp.status_code == 401

    def test_stale_timestamp_returns_401(self, hmac_client: TestClient) -> None:
        import time as _time

        body = directive("Alexa.PowerController", "TurnOn", endpoint_id="zdf")
        stale = int(_time.time()) - 3600
        resp = self._post(hmac_client, body, timestamp=stale)
        assert resp.status_code == 401
