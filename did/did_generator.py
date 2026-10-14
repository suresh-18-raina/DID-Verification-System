"""DID creation. The DID is derived from the public key, so it is
self-certifying: nobody can claim a DID without owning the matching key."""
import re

from config import config
from crypto.hashing import sha256_hex

_DID_RE = re.compile(r"^did:%s:[0-9a-f]{32}$" % config.DID_METHOD)


def generate_did(public_key_hex: str) -> str:
    digest = sha256_hex(bytes.fromhex(public_key_hex))
    return f"did:{config.DID_METHOD}:{digest[:32]}"


def is_valid_did(did) -> bool:
    return isinstance(did, str) and bool(_DID_RE.match(did))


def did_to_folder(did: str) -> str:
    """Folder-safe id (colons are not allowed in Windows file names)."""
    if not is_valid_did(did):
        raise ValueError("Invalid DID format.")
    return did.split(":")[-1]
