"""M3's HMAC-SHA256 and constant-time comparison with a caller-supplied key."""

import hashlib
import hmac


def generate_hmac(data_bytes: bytes, key: bytes) -> bytes:
    return hmac.new(key, data_bytes, hashlib.sha256).digest()


def verify_hmac(data_bytes: bytes, provided_tag: bytes, key: bytes) -> bool:
    return isinstance(provided_tag, bytes) and hmac.compare_digest(
        generate_hmac(data_bytes, key), provided_tag
    )
