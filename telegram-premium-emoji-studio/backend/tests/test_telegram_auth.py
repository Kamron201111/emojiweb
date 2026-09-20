"""Tests for Telegram initData cryptographic validation (stdlib-only)."""
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.core.telegram_auth import InitDataError, validate_init_data

BOT_TOKEN = "123456:TEST_TOKEN_ABC"


def _sign(fields: dict, token: str) -> str:
    """Build a valid initData string signed like Telegram does."""
    data_check = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": h})


def _valid_fields(**over):
    user = {"id": 42, "first_name": "Ali", "username": "ali", "language_code": "uz"}
    fields = {
        "user": json.dumps(user, separators=(",", ":")),
        "auth_date": str(int(time.time())),
        "query_id": "AAABBB",
    }
    fields.update(over)
    return fields


def test_valid_initdata_passes():
    init = _sign(_valid_fields(), BOT_TOKEN)
    data = validate_init_data(init, BOT_TOKEN)
    assert data.user.id == 42
    assert data.user.username == "ali"
    assert data.user.language_code == "uz"


def test_tampered_hash_rejected():
    init = _sign(_valid_fields(), BOT_TOKEN)
    tampered = init.replace("hash=", "hash=deadbeef")
    with pytest.raises(InitDataError):
        validate_init_data(tampered, BOT_TOKEN)


def test_wrong_token_rejected():
    init = _sign(_valid_fields(), BOT_TOKEN)
    with pytest.raises(InitDataError):
        validate_init_data(init, "999999:OTHER_TOKEN")


def test_forged_user_id_rejected():
    """An attacker can't just change the user id — the hash won't match."""
    fields = _valid_fields()
    init = _sign(fields, BOT_TOKEN)
    forged = init.replace("%22id%22%3A42", "%22id%22%3A999")
    with pytest.raises(InitDataError):
        validate_init_data(forged, BOT_TOKEN)


def test_expired_initdata_rejected():
    old = _valid_fields(auth_date=str(int(time.time()) - 100000))
    init = _sign(old, BOT_TOKEN)
    with pytest.raises(InitDataError):
        validate_init_data(init, BOT_TOKEN, max_age_seconds=3600)


def test_missing_hash_rejected():
    fields = _valid_fields()
    init = urlencode(fields)  # no hash
    with pytest.raises(InitDataError):
        validate_init_data(init, BOT_TOKEN)


def test_empty_initdata_rejected():
    with pytest.raises(InitDataError):
        validate_init_data("", BOT_TOKEN)


def test_missing_user_rejected():
    fields = {"auth_date": str(int(time.time()))}
    init = _sign(fields, BOT_TOKEN)
    with pytest.raises(InitDataError):
        validate_init_data(init, BOT_TOKEN)
