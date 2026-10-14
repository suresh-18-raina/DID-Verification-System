"""Central configuration. Paths are resolved at call time so tests can
point the app at a temporary folder with the DID_DATA_DIR variable."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"          # localhost only - never exposed to the network
PORT = 5000
DID_METHOD = "local"        # DIDs look like  did:local:<32 hex chars>
KEY_TYPE = "Ed25519"


def data_dir() -> Path:
    return Path(os.environ.get("DID_DATA_DIR", BASE_DIR / "data"))


def identities_dir() -> Path:
    return data_dir() / "identities"


def credentials_dir() -> Path:
    return data_dir() / "credentials"


def blockchain_dir() -> Path:
    return data_dir() / "blockchain"


def chain_file() -> Path:
    return blockchain_dir() / "chain.json"


def chain_backup_file() -> Path:
    return blockchain_dir() / "chain.backup.json"


def ensure_dirs() -> None:
    for d in (identities_dir(), credentials_dir(), blockchain_dir()):
        d.mkdir(parents=True, exist_ok=True)
