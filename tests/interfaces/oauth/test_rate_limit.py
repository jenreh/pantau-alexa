"""Rate limiting on /oauth/authorize (login) and /oauth/token."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tests.interfaces.oauth.conftest import (
    TEST_CLIENT_ID,
    TEST_REDIRECT_URI,
    make_pkce_pair,
)

from tiberio.adapters.auth_code_store import AuthCodeStore
from tiberio.adapters.jwt_service import JwtService
from tiberio.adapters.sqlite_user_store import SqliteUserStore
from tiberio.api.app import create_app
from tiberio.composition import build_oauth_test_container
from tiberio.config.settings import Settings
from tiberio.interfaces.rate_limit import SlidingWindowRateLimiter


class TestSlidingWindowRateLimiter:
    def test_allows_up_to_max_attempts(self) -> None:
        limiter = SlidingWindowRateLimiter(max_attempts=3, window_seconds=60)
        assert limiter.allow("k")
        assert limiter.allow("k")
        assert limiter.allow("k")
        assert not limiter.allow("k")

    def test_keys_are_independent(self) -> None:
        limiter = SlidingWindowRateLimiter(max_attempts=1, window_seconds=60)
        assert limiter.allow("a")
        assert limiter.allow("b")
        assert not limiter.allow("a")

    def test_window_expiry_frees_slots(self) -> None:
        limiter = SlidingWindowRateLimiter(max_attempts=1, window_seconds=0.0)
        assert limiter.allow("k")
        # window of 0 seconds → previous attempt immediately expired
        assert limiter.allow("k")


@pytest.fixture
async def limited_client(tmp_path: Path) -> AsyncGenerator[TestClient]:
    """App with a tight rate limit (3 attempts / 60 s) for endpoint tests."""
    cfg = tmp_path / "devices.yaml"
    cfg.write_text(
        """
tv:
  watch_activity: "TV"
  audio:
    id: "tv-audio"
    friendly_name: "Fernseher"
  channels: []
blinds: []
thermostats: []
""",
        encoding="utf-8",
    )
    settings = Settings(
        jwt_secret=SecretStr("rate-limit-test-secret-0123456789"),
        dev_mode=True,
        oauth_allowed_redirect_uris=[TEST_REDIRECT_URI],
        rate_limit_max_attempts=3,
        rate_limit_window_seconds=60,
    )
    store = SqliteUserStore(":memory:")
    await store.start()
    container = build_oauth_test_container(
        cfg, store, JwtService(settings.jwt_secret.get_secret_value()), AuthCodeStore()
    )
    app = create_app(settings=settings, container=container)
    yield TestClient(app, follow_redirects=False)
    await store.stop()


def _login_attempt(client: TestClient, username: str = "nobody") -> int:
    _, challenge = make_pkce_pair()
    resp = client.post(
        "/oauth/authorize",
        data={
            "username": username,
            "password": "wrong",
            "redirect_uri": TEST_REDIRECT_URI,
            "client_id": TEST_CLIENT_ID,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
    )
    return resp.status_code


class TestLoginRateLimit:
    async def test_excess_login_attempts_return_429(
        self, limited_client: TestClient
    ) -> None:
        for _ in range(3):
            assert _login_attempt(limited_client) == 401
        assert _login_attempt(limited_client) == 429

    async def test_limit_is_per_username(self, limited_client: TestClient) -> None:
        for _ in range(3):
            _login_attempt(limited_client, username="alice")
        assert _login_attempt(limited_client, username="alice") == 429
        assert _login_attempt(limited_client, username="bob") == 401

    async def test_username_spraying_hits_ip_wide_limit(
        self, limited_client: TestClient
    ) -> None:
        """Rotating usernames must not bypass throttling (3x per-IP bucket = 9)."""
        for i in range(9):
            assert _login_attempt(limited_client, username=f"user-{i}") == 401
        assert _login_attempt(limited_client, username="user-fresh") == 429


class TestTokenRateLimit:
    async def test_excess_token_requests_return_429(
        self, limited_client: TestClient
    ) -> None:
        for _ in range(3):
            resp = limited_client.post(
                "/oauth/token",
                data={"grant_type": "refresh_token", "refresh_token": "bad"},
            )
            assert resp.status_code == 400
        resp = limited_client.post(
            "/oauth/token",
            data={"grant_type": "refresh_token", "refresh_token": "bad"},
        )
        assert resp.status_code == 429
        assert resp.json()["error"] == "rate_limited"
