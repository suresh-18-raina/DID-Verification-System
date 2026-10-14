"""Digital signatures with Ed25519."""
from cryptography.exceptions import InvalidSignature


def sign(private_key, message: bytes) -> str:
    """Return the signature as a hex string."""
    return private_key.sign(message).hex()


def verify(public_key, signature_hex: str, message: bytes) -> bool:
    """True only if signature_hex was produced by the matching private key for exactly this message."""
    try:
        public_key.verify(bytes.fromhex(signature_hex), message)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
