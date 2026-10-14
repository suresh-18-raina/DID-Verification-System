"""DID Document = the public description of an identity (never contains the private key)."""
from datetime import datetime, timezone

from config import config
from crypto.hashing import hash_object


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_did_document(did: str, public_key_hex: str, name: str, role: str) -> dict:
    key_id = f"{did}#key-1"
    return {
        "id": did,
        "created": now_iso(),
        "profile": {"name": name, "role": role},
        "verificationMethod": [{
            "id": key_id,
            "type": "Ed25519VerificationKey",
            "controller": did,
            "publicKeyHex": public_key_hex,
        }],
        "authentication": [key_id],
        "assertionMethod": [key_id],
    }


def document_hash(doc: dict) -> str:
    return hash_object(doc)


def get_public_key_hex(doc: dict) -> str:
    return doc["verificationMethod"][0]["publicKeyHex"]
