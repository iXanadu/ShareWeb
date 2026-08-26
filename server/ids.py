"""Prefixed ULIDs (Crockford base32) and opaque secrets."""

from __future__ import annotations

import os
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode_crockford(value: int, length: int) -> str:
    chars = ["0"] * length
    for i in range(length - 1, -1, -1):
        chars[i] = _CROCKFORD[value & 31]
        value >>= 5
    return "".join(chars)


def ulid() -> str:
    """26-char Crockford ULID: 48-bit timestamp + 80-bit randomness."""
    ts = int(time.time() * 1000) & ((1 << 48) - 1)
    rand = int.from_bytes(os.urandom(10), "big")
    return _encode_crockford(ts, 10) + _encode_crockford(rand, 16)


def prefixed(prefix: str) -> str:
    return f"{prefix}_{ulid()}"


def new_api_token_secret() -> str:
    """shr_ + 43-char base64url (256 bits of entropy, no padding)."""
    import base64

    raw = os.urandom(32)
    return "shr_" + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def new_session_secret() -> str:
    import base64

    return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii").rstrip("=")
