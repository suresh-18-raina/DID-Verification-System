# Decentralized Identity (DID) Verification System

A Cryptography PBL project: create decentralized identities, issue digitally signed student credentials,
and verify them with a tamper-evident local ledger. **No database. Runs on localhost.**

## Introduction
Traditional identity systems depend on one organisation's database. Here, an identity is a key pair
and a DID derived from the public key. A credential is trusted because of a digital signature that anyone
can check with the issuer's public key, not because a server says so.

## Objectives
- Show public-key cryptography (Ed25519) and hashing (SHA-256) in a working application.
- Demonstrate that any change to a credential is detected.
- Demonstrate a hash-linked ledger and how it exposes tampering.

## Features
| Feature | What it shows |
|---|---|
| DID + DID Document | Self-certifying identifier: `did:local:` + first 32 hex chars of SHA-256(public key) |
| Key generation | Ed25519 key pair; private key stored as `private_key.pem`, never displayed or served |
| Credential issuing | Canonical JSON -> SHA-256 -> Ed25519 signature |
| 8-check verifier | Format, issuer found, issuer unchanged, hash, signature, ledger record, ledger integrity, revocation |
| Local ledger | Blocks for DID registration, issuance and revocation, each linked by `previous_hash` |
| Revocation | Issuer signs `revoke:<credential_id>`; recorded on the ledger |
| Tamper lab | Edit a block (with or without recalculating its hash), watch validation fail, then restore |
| Guided demo | One click creates an issuer, a student and a credential and opens the verifier |
| Tamper demo | One click edits the credential text so verification visibly fails |
| Storage | JSON files only (`data/`) |

## Technologies Used
Python 3.10+, Flask, `cryptography` (Ed25519), `hashlib` (SHA-256), HTML/CSS/vanilla JavaScript, JSON files.

## System Architecture
```
Browser (localhost:5000) -> Flask (app.py)
                              |-- did/          identities, DID documents
                              |-- credentials/  issue, revoke, verify
                              |-- blockchain/   blocks, chain validation
                              |-- crypto/       Ed25519 + SHA-256
                              `-- storage/      JSON files in data/
```

## Cryptographic Algorithms
- **Ed25519**: signing and verification.
- **SHA-256**: credential fingerprints, block hashes, DID derivation, DID document fingerprint.
- **Canonical JSON** (`sort_keys=True`, no spaces): the same data always gives the same hash.

Workflow: `credential (without proof) -> canonical JSON -> SHA-256 -> sign hash with issuer private key -> proof{hash, signature}`

## Project Structure
```
did-verification-system/
├── app.py                  Flask routes + REST API
├── requirements.txt
├── config/config.py        paths, host, port
├── crypto/                 keys.py, hashing.py, signatures.py
├── did/                    did_generator.py, did_document.py, identity_manager.py
├── credentials/            issuer.py, verifier.py
├── blockchain/             block.py, chain.py
├── storage/json_storage.py atomic JSON read/write (replaces a database)
├── data/                   identities/, credentials/, blockchain/  (generated; git-ignored)
├── templates/              9 HTML pages (Jinja)
├── static/css, static/js   styling and front-end logic
└── tests/                  31 unit and API tests
```
Generated layout: `data/identities/<id>/{did.json, private_key.pem}`, `data/credentials/<cred-id>.json`, `data/blockchain/chain.json`.

## Installation
```bash
python -m venv venv
venv\Scripts\activate          # Windows      (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

## Running the Application
```bash
python app.py
```
Open http://127.0.0.1:5000

## Viva demo script (about 3 minutes)
1. Home -> **Run the guided demo** (creates issuer + student + credential, then verifies: 8/8 pass).
2. Click **Tamper with it (demo)** then **Verify**: hash, signature and ledger checks fail.
3. Ledger page -> Tamper lab: edit block 2 with "recalculate hash" ticked; block 3's link breaks.
4. Click **Restore original**.
5. Credentials page -> **Revoke**, then verify again: "Not revoked" fails.

## REST API
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/identity/create` | `{name, role}` |
| GET | `/api/identity` | list identities |
| POST | `/api/credential/issue` | `{issuer_did, holder_did?, name, student_id, department, course}` |
| GET | `/api/credential`, `/api/credential/<id>` | list / fetch |
| POST | `/api/credential/verify` | `{credential}` |
| POST | `/api/credential/<id>/revoke` | revoke |
| GET | `/api/blockchain`, `/api/blockchain/validate` | ledger and validation |
| POST | `/api/blockchain/tamper`, `/api/blockchain/restore` | teaching lab |

## Testing
```bash
python -m unittest discover -s tests -t . -v
```
Tests use a temporary folder, so your real `data/` is never touched.

## Security Considerations
- The server binds to 127.0.0.1 only; private keys are never returned by any route or served as static files.
- DIDs and credential IDs are validated by regex before touching the file system (no path traversal).
- All user text is escaped in the browser (no HTML injection).
- The DID Document hash is anchored on the ledger, so swapping an issuer's public key is detected.

## Limitations
- Single-machine prototype: there is no real network of nodes, so "decentralized" is simulated.
- Private keys are stored unencrypted in PEM files (fine for a lab, not for production).
- If an attacker rewrites the *newest* block and recomputes its hash, hash-linking alone cannot expose it
  (later blocks or a network of peers would). The Tamper lab explains this.
- No login system; anyone using the browser can act as any local issuer.

## Future Enhancements
W3C DID / Verifiable Credentials compatibility, multi-node ledger, passphrase-protected keys, selective
disclosure / zero-knowledge proofs, QR-code credentials, mobile wallet.
