import unittest
from tests import base  # noqa: F401  (sets sys.path)
from crypto.keys import generate_key_pair, public_key_to_hex, public_key_from_hex
from crypto.hashing import hash_object, sha256_hex
from crypto.signatures import sign, verify


class CryptoTests(unittest.TestCase):
    def test_key_generation(self):
        private_key, public_key = generate_key_pair()
        self.assertEqual(len(public_key_to_hex(public_key)), 64)  # 32 bytes
        self.assertIsNotNone(private_key)

    def test_public_key_round_trip(self):
        _, pub = generate_key_pair()
        self.assertEqual(public_key_to_hex(public_key_from_hex(public_key_to_hex(pub))), public_key_to_hex(pub))

    def test_sha256_known_value(self):
        self.assertEqual(sha256_hex(b"abc"),
                         "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_canonical_hash_ignores_key_order(self):
        self.assertEqual(hash_object({"a": 1, "b": 2}), hash_object({"b": 2, "a": 1}))

    def test_valid_signature(self):
        priv, pub = generate_key_pair()
        sig = sign(priv, b"Hello DID")
        self.assertTrue(verify(pub, sig, b"Hello DID"))

    def test_modified_message_fails(self):
        priv, pub = generate_key_pair()
        sig = sign(priv, b"Hello DID")
        self.assertFalse(verify(pub, sig, b"Hello Hacker"))

    def test_wrong_key_fails(self):
        priv, _ = generate_key_pair()
        _, other_pub = generate_key_pair()
        self.assertFalse(verify(other_pub, sign(priv, b"x"), b"x"))

    def test_garbage_signature_fails(self):
        _, pub = generate_key_pair()
        self.assertFalse(verify(pub, "not-hex", b"x"))


if __name__ == "__main__":
    unittest.main()
