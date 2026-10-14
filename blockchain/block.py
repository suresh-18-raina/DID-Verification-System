"""A single block of the local ledger."""
from dataclasses import dataclass, field, asdict

from crypto.hashing import hash_object


@dataclass
class Block:
    index: int
    timestamp: str
    type: str                 # GENESIS | DID_REGISTERED | CREDENTIAL_ISSUED | CREDENTIAL_REVOKED
    data: dict
    previous_hash: str
    hash: str = field(default="")

    def compute_hash(self) -> str:
        """SHA-256 over every field except the hash itself."""
        return hash_object({
            "index": self.index,
            "timestamp": self.timestamp,
            "type": self.type,
            "data": self.data,
            "previous_hash": self.previous_hash,
        })

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Block":
        return cls(index=d["index"], timestamp=d["timestamp"], type=d["type"],
                   data=d["data"], previous_hash=d["previous_hash"], hash=d.get("hash", ""))
