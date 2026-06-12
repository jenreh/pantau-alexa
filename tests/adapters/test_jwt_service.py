"""Tests for JwtService — JWT issuing and validation."""

from __future__ import annotations

import pytest

from tiberio.adapters.jwt_service import JwtService
from tiberio.ports.token_validator_port import TokenClaims

TEST_SECRET = "super-secret-test-key"  # noqa: S105


@pytest.fixture
def service() -> JwtService:
    return JwtService(TEST_SECRET, access_token_expire_minutes=60)


class TestIssueAccessToken:
    def test_returns_token_string_and_expires_in(self, service: JwtService) -> None:
        token, expires_in = service.issue_access_token("user-123")
        assert isinstance(token, str)
        assert len(token) > 0
        assert expires_in == 3600

    def test_token_is_decodable(self, service: JwtService) -> None:
        token, _ = service.issue_access_token("user-abc")
        claims = service.validate(token)
        assert claims.user_id == "user-abc"

    def test_token_carries_alexa_scope(self, service: JwtService) -> None:
        token, _ = service.issue_access_token("user-abc")
        claims = service.validate(token)
        assert claims.scope == "alexa"

    def test_different_users_produce_different_tokens(
        self, service: JwtService
    ) -> None:
        t1, _ = service.issue_access_token("alice")
        t2, _ = service.issue_access_token("bob")
        assert t1 != t2


class TestIssueRefreshToken:
    def test_returns_non_empty_string(self, service: JwtService) -> None:
        token = service.issue_refresh_token()
        assert isinstance(token, str)
        assert len(token) > 10

    def test_tokens_are_unique(self, service: JwtService) -> None:
        tokens = {service.issue_refresh_token() for _ in range(10)}
        assert len(tokens) == 10


class TestValidate:
    def test_valid_token_returns_claims(self, service: JwtService) -> None:
        token, _ = service.issue_access_token("user-42")
        claims = service.validate(token)
        assert isinstance(claims, TokenClaims)
        assert claims.user_id == "user-42"

    def test_invalid_token_raises_value_error(self, service: JwtService) -> None:
        with pytest.raises(ValueError):
            service.validate("not.a.valid.jwt")

    def test_token_from_different_secret_raises_value_error(self) -> None:
        other_service = JwtService("different-secret")
        token, _ = other_service.issue_access_token("user-x")

        original = JwtService(TEST_SECRET, access_token_expire_minutes=60)
        with pytest.raises(ValueError):
            original.validate(token)

    def test_empty_token_raises_value_error(self, service: JwtService) -> None:
        with pytest.raises(ValueError):
            service.validate("")

    def test_expired_token_raises_value_error(self) -> None:
        service = JwtService("test-key", access_token_expire_minutes=0)
        # Issue with 0-minute expiry → token is immediately expired
        # We can't easily travel in time, so test with a manipulated payload instead
        from jose import jwt as jose_jwt

        payload = {"sub": "user-x", "scope": "alexa", "exp": 1}  # epoch 1 = long ago
        token = jose_jwt.encode(payload, "test-key", algorithm="HS256")
        with pytest.raises(ValueError):
            service.validate(token)
