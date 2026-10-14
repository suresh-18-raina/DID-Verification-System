"""Decentralized Identity (DID) Verification System - Flask app (localhost only, no database)."""
import json

from flask import Flask, jsonify, render_template, request, abort, Response

from config import config
from blockchain.chain import Blockchain, ChainError
from credentials import issuer as issuer_service
from credentials.verifier import verify_credential
from did import identity_manager as ids
from did.did_generator import is_valid_did
from storage.json_storage import clear_directory


def create_app() -> Flask:
    app = Flask(__name__)
    config.ensure_dirs()
    Blockchain().ensure_genesis()

    # ---------- helpers ----------
    def body() -> dict:
        return request.get_json(silent=True) or {}

    def stats() -> dict:
        chain = Blockchain()
        return {
            "identities": len(ids.list_identities()),
            "credentials": len(issuer_service.list_credentials()),
            "blocks": len(chain.blocks()),
            "chain_valid": chain.validate()["valid"],
        }

    @app.errorhandler(ValueError)
    def bad_request(e):
        return jsonify(success=False, error=str(e)), 400

    @app.errorhandler(ChainError)
    def conflict(e):
        return jsonify(success=False, error=str(e)), 409

    @app.context_processor
    def inject_globals():
        return {"nav_stats": stats()}

    # ---------- pages ----------
    @app.get("/")
    def index():
        return render_template("index.html", page="home")

    @app.get("/create-identity")
    def create_identity_page():
        return render_template("create_identity.html", page="create")

    @app.get("/identities")
    def identities_page():
        return render_template("identities.html", page="identities", identities=ids.list_identities())

    @app.get("/identity/<folder>")
    def identity_page(folder):
        match = next((i for i in ids.list_identities() if i["folder"] == folder), None)
        if not match:
            abort(404)
        doc = ids.resolve_did(match["did"])
        issued = [c for c in issuer_service.list_credentials() if c["issuer"] == match["did"]]
        return render_template("identity.html", page="identities", identity=match,
                               document=json.dumps(doc, indent=2), issued=issued)

    @app.get("/issue-credential")
    def issue_page():
        return render_template("issue_credential.html", page="issue",
                               issuers=ids.list_identities("issuer"), holders=ids.list_identities("holder"))

    @app.get("/credentials")
    def credentials_page():
        return render_template("credentials.html", page="credentials", credentials=issuer_service.list_credentials())

    @app.get("/verify")
    def verify_page():
        return render_template("verify.html", page="verify", credentials=issuer_service.list_credentials())

    @app.get("/blockchain")
    def blockchain_page():
        return render_template("blockchain.html", page="ledger")

    # ---------- API: identity ----------
    @app.post("/api/identity/create")
    def api_create_identity():
        data = body()
        result = ids.create_identity(data.get("name"), data.get("role", "holder"))
        return jsonify(success=True, did=result["did"], document=result["document"],
                       folder=result["did"].split(":")[-1], block_index=result["block_index"])

    @app.get("/api/identity")
    def api_list_identities():
        return jsonify(success=True, identities=ids.list_identities(request.args.get("role")))

    # ---------- API: credentials ----------
    @app.post("/api/credential/issue")
    def api_issue():
        data = body()
        result = issuer_service.issue_credential(data.get("issuer_did"), data, data.get("holder_did") or None)
        return jsonify(success=True, **result)

    @app.get("/api/credential")
    def api_list_credentials():
        return jsonify(success=True, credentials=issuer_service.list_credentials())

    @app.get("/api/credential/<cid>")
    def api_get_credential(cid):
        c = issuer_service.load_credential(cid)
        if not c:
            return jsonify(success=False, error="Credential not found."), 404
        return jsonify(success=True, credential=c)

    @app.get("/api/credential/<cid>/download")
    def api_download(cid):
        c = issuer_service.load_credential(cid)
        if not c:
            abort(404)
        return Response(json.dumps(c, indent=2), mimetype="application/json",
                        headers={"Content-Disposition": f"attachment; filename={cid}.json"})

    @app.post("/api/credential/verify")
    def api_verify():
        credential = body().get("credential")
        if isinstance(credential, str):
            try:
                credential = json.loads(credential)
            except json.JSONDecodeError as e:
                return jsonify(success=False, error=f"That text is not valid JSON ({e.msg} at line {e.lineno}).")
        return jsonify(success=True, **verify_credential(credential))

    @app.post("/api/credential/<cid>/revoke")
    def api_revoke(cid):
        return jsonify(success=True, **issuer_service.revoke_credential(cid))

    # ---------- API: ledger ----------
    @app.get("/api/blockchain")
    def api_chain():
        chain = Blockchain()
        v = chain.validate()
        return jsonify(success=True, blocks=chain.annotated_blocks(), valid=v["valid"],
                       first_invalid=v["first_invalid"], has_backup=chain.has_backup())

    @app.get("/api/blockchain/validate")
    def api_chain_validate():
        v = Blockchain().validate()
        v.pop("status")
        return jsonify(success=True, **v)

    @app.post("/api/blockchain/tamper")
    def api_tamper():
        data = body()
        try:
            index = int(data.get("index"))
        except (TypeError, ValueError):
            raise ValueError("Choose a block number.")
        result = Blockchain().simulate_tamper(index, bool(data.get("recompute")))
        return jsonify(success=True, **result)

    @app.post("/api/blockchain/restore")
    def api_restore():
        return jsonify(success=True, restored=Blockchain().restore_backup())

    # ---------- API: demo helpers ----------
    @app.post("/api/demo/seed")
    def api_seed():
        issuer = ids.create_identity("Greenfield University", "issuer")
        holder = ids.create_identity("Asha Rao", "holder")
        result = issuer_service.issue_credential(
            issuer["did"],
            {"name": "Asha Rao", "student_id": "CS101", "department": "Computer Science",
             "course": "B.Tech Cryptography"},
            holder["did"])
        return jsonify(success=True, credential_id=result["credential"]["credential_id"])

    @app.post("/api/reset")
    def api_reset():
        for d in (config.identities_dir(), config.credentials_dir(), config.blockchain_dir()):
            clear_directory(d)
        Blockchain().ensure_genesis()
        return jsonify(success=True)

    return app


if __name__ == "__main__":
    app = create_app()
    print(f"\n  DID Verification System running at http://{config.HOST}:{config.PORT}\n")
    app.run(host=config.HOST, port=config.PORT, debug=False)
