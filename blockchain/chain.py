"""A small tamper-evident ledger stored in data/blockchain/chain.json.

No mining, no network - each block simply stores the hash of the block
before it, so changing any old block breaks every link after it."""
import shutil
import threading
from datetime import datetime, timezone

from config import config
from blockchain.block import Block
from storage.json_storage import load_json, save_json

GENESIS_PREVIOUS_HASH = "0" * 64
_lock = threading.RLock()


class ChainError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class Blockchain:
    def __init__(self, path=None):
        self.path = path or config.chain_file()

    # ---------- storage ----------
    def _load(self) -> list:
        return load_json(self.path, []) or []

    def _save(self, blocks: list) -> None:
        save_json(self.path, blocks)

    def ensure_genesis(self) -> None:
        with _lock:
            if self._load():
                return
            genesis = Block(0, _now(), "GENESIS", {"message": "DID Verification System ledger created"},
                            GENESIS_PREVIOUS_HASH)
            genesis.hash = genesis.compute_hash()
            self._save([genesis.to_dict()])

    def blocks(self) -> list:
        self.ensure_genesis()
        return self._load()

    # ---------- writing ----------
    def add_block(self, block_type: str, data: dict) -> Block:
        with _lock:
            self.ensure_genesis()
            if not self.validate()["valid"]:
                raise ChainError("The ledger is currently invalid (it was tampered with). "
                                 "Restore it on the Ledger page before adding new records.")
            blocks = self._load()
            last = Block.from_dict(blocks[-1])
            block = Block(last.index + 1, _now(), block_type, data, last.hash)
            block.hash = block.compute_hash()
            blocks.append(block.to_dict())
            self._save(blocks)
            return block

    # ---------- validation ----------
    def validate(self) -> dict:
        """Re-check every hash and every link. Returns per-block results."""
        blocks = self._load()
        errors, status = [], {}
        for i, raw in enumerate(blocks):
            problem = None
            try:
                block = Block.from_dict(raw)
                if block.index != i:
                    problem = "Block number is out of order."
                elif block.compute_hash() != block.hash:
                    problem = "Block contents no longer match its stored hash."
                else:
                    expected_prev = GENESIS_PREVIOUS_HASH if i == 0 else blocks[i - 1].get("hash")
                    if block.previous_hash != expected_prev:
                        problem = f"Link broken: previous_hash does not match the hash of block #{i - 1}."
            except (KeyError, TypeError):
                problem = "Block is malformed."
            status[i] = problem
            if problem:
                errors.append({"index": i, "problem": problem})
        return {
            "valid": not errors,
            "length": len(blocks),
            "errors": errors,
            "first_invalid": errors[0]["index"] if errors else None,
            "status": status,
        }

    def annotated_blocks(self) -> list:
        result = self.validate()
        out = []
        for i, b in enumerate(self.blocks()):
            out.append({**b, "valid": result["status"].get(i) is None, "problem": result["status"].get(i)})
        return out

    # ---------- lookups ----------
    def find_did_block(self, did: str):
        for b in self.blocks():
            if b["type"] == "DID_REGISTERED" and b["data"].get("did") == did:
                return b
        return None

    def find_credential_block(self, credential_id: str):
        for b in self.blocks():
            if b["type"] == "CREDENTIAL_ISSUED" and b["data"].get("credential_id") == credential_id:
                return b
        return None

    def find_revocation(self, credential_id: str):
        for b in self.blocks():
            if b["type"] == "CREDENTIAL_REVOKED" and b["data"].get("credential_id") == credential_id:
                return b
        return None

    def revoked_ids(self) -> set:
        return {b["data"].get("credential_id") for b in self.blocks() if b["type"] == "CREDENTIAL_REVOKED"}

    # ---------- tamper lab (teaching feature) ----------
    def simulate_tamper(self, index: int, recompute_hash: bool = False) -> dict:
        """Edit a block on purpose so the validator can catch it.

        recompute_hash=False -> a clumsy attacker: block hash no longer matches contents.
        recompute_hash=True  -> a smart attacker: block hash is fixed, but the NEXT block's
                                previous_hash link breaks."""
        with _lock:
            blocks = self.blocks()
            if not 0 <= index < len(blocks):
                raise ChainError("That block does not exist.")
            if not config.chain_backup_file().exists():
                shutil.copyfile(self.path, config.chain_backup_file())
            block = Block.from_dict(blocks[index])
            if "credential_hash" in block.data:
                h = block.data["credential_hash"]
                block.data["credential_hash"] = h[:-1] + ("0" if h[-1] != "0" else "1")
            else:
                block.data["tampered_note"] = "edited by attacker"
            if recompute_hash:
                block.hash = block.compute_hash()
            blocks[index] = block.to_dict()
            self._save(blocks)
            note = None
            if recompute_hash and index == len(blocks) - 1:
                note = ("This is the newest block, so no later block exists to expose the change. "
                        "That is why real ledgers keep growing: every new block 'seals' the ones before it.")
            return {"note": note}

    def has_backup(self) -> bool:
        return config.chain_backup_file().exists()

    def restore_backup(self) -> bool:
        with _lock:
            backup = config.chain_backup_file()
            if not backup.exists():
                return False
            shutil.copyfile(backup, self.path)
            backup.unlink()
            return True
