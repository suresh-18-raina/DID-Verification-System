"""Create, load and list identities (files under data/identities/<id>/)."""
from config import config
from blockchain.chain import Blockchain
from crypto.keys import generate_key_pair, public_key_to_hex, save_private_key, load_private_key
from did.did_generator import generate_did, is_valid_did, did_to_folder
from did.did_document import build_did_document, document_hash, get_public_key_hex
from storage.json_storage import save_json, load_json, list_json

ROLES = ("issuer", "holder")


def _identity_folder(did: str):
    return config.identities_dir() / did_to_folder(did)


def create_identity(name: str, role: str = "holder") -> dict:
    name = (name or "").strip()
    if not name or len(name) > 80:
        raise ValueError("Please enter a name between 1 and 80 characters.")
    if role not in ROLES:
        raise ValueError("Role must be 'issuer' or 'holder'.")

    private_key, public_key = generate_key_pair()
    public_hex = public_key_to_hex(public_key)
    did = generate_did(public_hex)
    doc = build_did_document(did, public_hex, name, role)

    folder = _identity_folder(did)
    save_json(folder / "did.json", doc)
    save_private_key(private_key, folder / "private_key.pem")

    # Anchor the DID Document hash on the ledger so later edits are detectable.
    block = Blockchain().add_block("DID_REGISTERED", {
        "did": did,
        "role": role,
        "did_document_hash": document_hash(doc),
    })
    return {"did": did, "document": doc, "block_index": block.index}


def resolve_did(did: str):
    """Return the DID document or None. Validates the DID first (blocks path tricks)."""
    if not is_valid_did(did):
        return None
    return load_json(_identity_folder(did) / "did.json")


def get_private_key(did: str):
    if not is_valid_did(did):
        raise ValueError("Invalid DID.")
    path = _identity_folder(did) / "private_key.pem"
    if not path.exists():
        raise ValueError("The private key for this identity is not on this computer.")
    return load_private_key(path)


def list_identities(role: str = None) -> list:
    items = []
    for p in list_json_dirs():
        doc = load_json(p / "did.json")
        if not doc:
            continue
        if role and doc["profile"]["role"] != role:
            continue
        items.append({
            "did": doc["id"],
            "folder": did_to_folder(doc["id"]),
            "name": doc["profile"]["name"],
            "role": doc["profile"]["role"],
            "created": doc["created"],
            "public_key": get_public_key_hex(doc),
        })
    return sorted(items, key=lambda i: i["created"])


def list_json_dirs():
    base = config.identities_dir()
    return sorted(p for p in base.iterdir() if p.is_dir()) if base.exists() else []
