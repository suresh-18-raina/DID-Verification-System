import os
from tests.base import TempDataTestCase
from did import identity_manager as ids
from did.did_generator import is_valid_did
from config import config


class DIDTests(TempDataTestCase):
    def test_create_identity(self):
        r = ids.create_identity("Alice", "holder")
        self.assertTrue(is_valid_did(r["did"]))
        self.assertEqual(ids.resolve_did(r["did"])["profile"]["name"], "Alice")

    def test_private_key_not_in_did_document(self):
        r = ids.create_identity("Alice", "holder")
        self.assertNotIn("PRIVATE", str(r["document"]))
        folder = config.identities_dir() / r["did"].split(":")[-1]
        self.assertTrue((folder / "private_key.pem").exists())

    def test_did_is_registered_on_ledger(self):
        from blockchain.chain import Blockchain
        r = ids.create_identity("Uni", "issuer")
        self.assertIsNotNone(Blockchain().find_did_block(r["did"]))

    def test_validation(self):
        with self.assertRaises(ValueError):
            ids.create_identity("", "holder")
        with self.assertRaises(ValueError):
            ids.create_identity("Bob", "admin")

    def test_resolve_rejects_path_tricks(self):
        self.assertIsNone(ids.resolve_did("did:local:../../etc/passwd"))


if __name__ == "__main__":
    import unittest
    unittest.main()
