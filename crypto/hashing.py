"""SHA-256 hashing with canonical JSON.

Canonical JSON = keys sorted, no spaces. It guarantees that the same data
always produces the same bytes, and therefore the same hash."""
import hashlib
import json


def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_object(obj) -> str:
    """SHA-256 of the canonical JSON form of any JSON-serialisable object."""
    return sha256_hex(canonical_json(obj))
