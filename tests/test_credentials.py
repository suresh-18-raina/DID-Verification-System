import copy
import json
from tests.base import TempDataTestCase
from config import config
from did import identity_manager as ids
from credentials import issuer
from credentials.verifier import verify_credential

FIELDS = {"name": "Rahul", "student_id": "CS101", "department": "CSE", "course": "Cryptography"}


class CredentialTests(TempDataTestCase):
    def setUp(self):
        super().setUp()
        self.issuer = ids.create_identity("Uni", "issuer")["did"]
        self.cred = issuer.issue_credential(self.issuer, FIELDS)["credential"]

    def test_valid_credential_passes_all_checks(self):
        r = verify_credential(self.cred)
        self.assertTrue(r["valid"], r["checks"])
        self.assertEqual(r["passed"], 8)

    def test_modified_credential_fails(self):
        bad = copy.deepcopy(self.cred)
        bad["subject"]["student_id"] = "CS999"
        r = verify_credential(bad)
        status = {c["id"]: c["status"] for c in r["checks"]}
        self.assertFalse(r["valid"])
        self.assertEqual(status["hash"], "fail")
        self.assertEqual(status["signature"], "fail")

    def test_modified_but_rehashed_credential_fails_signature(self):
        from crypto.hashing import hash_object
        bad = copy.deepcopy(self.cred)
        bad["subject"]["name"] = "Mallory"
        bad["proof"]["hash"] = hash_object({k: v for k, v in bad.items() if k != "proof"})
        status = {c["id"]: c["status"] for c in verify_credential(bad)["checks"]}
        self.assertEqual(status["hash"], "pass")
        self.assertEqual(status["signature"], "fail")

    def test_forged_by_other_identity_fails(self):
        mallory = ids.create_identity("Mallory", "issuer")["did"]
        forged = issuer.issue_credential(mallory, FIELDS)["credential"]
        forged["issuer"] = self.issuer          # claim the real university signed it
        self.assertFalse(verify_credential(forged)["valid"])

    def test_malformed_input(self):
        self.assertFalse(verify_credential({"hello": "world"})["valid"])
        self.assertFalse(verify_credential([1, 2])["valid"])

    def test_holders_cannot_issue(self):
        holder = ids.create_identity("Student", "holder")["did"]
        with self.assertRaises(ValueError):
            issuer.issue_credential(holder, FIELDS)

    def test_revocation(self):
        issuer.revoke_credential(self.cred["credential_id"])
        r = verify_credential(self.cred)
        self.assertFalse(r["valid"])
        self.assertEqual({c["id"]: c["status"] for c in r["checks"]}["revocation"], "fail")

    def test_swapped_public_key_is_detected(self):
        path = config.identities_dir() / self.issuer.split(":")[-1] / "did.json"
        doc = json.loads(path.read_text())
        doc["verificationMethod"][0]["publicKeyHex"] = "00" * 32
        path.write_text(json.dumps(doc))
        r = verify_credential(self.cred)
        self.assertEqual({c["id"]: c["status"] for c in r["checks"]}["anchor"], "fail")
        self.assertFalse(r["valid"])


if __name__ == "__main__":
    import unittest
    unittest.main()
