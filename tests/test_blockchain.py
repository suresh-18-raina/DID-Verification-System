from tests.base import TempDataTestCase
from blockchain.chain import Blockchain, ChainError


class BlockchainTests(TempDataTestCase):
    def test_genesis_block(self):
        chain = Blockchain()
        blocks = chain.blocks()
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["type"], "GENESIS")
        self.assertEqual(blocks[0]["previous_hash"], "0" * 64)

    def test_add_blocks_and_validate(self):
        chain = Blockchain()
        chain.add_block("CREDENTIAL_ISSUED", {"credential_id": "a", "credential_hash": "ab" * 32})
        chain.add_block("CREDENTIAL_ISSUED", {"credential_id": "b", "credential_hash": "cd" * 32})
        blocks = chain.blocks()
        self.assertEqual(blocks[2]["previous_hash"], blocks[1]["hash"])
        self.assertTrue(chain.validate()["valid"])

    def test_tampering_is_detected(self):
        chain = Blockchain()
        chain.add_block("CREDENTIAL_ISSUED", {"credential_id": "a", "credential_hash": "ab" * 32})
        chain.add_block("CREDENTIAL_ISSUED", {"credential_id": "b", "credential_hash": "cd" * 32})
        chain.simulate_tamper(1)
        v = chain.validate()
        self.assertFalse(v["valid"])
        self.assertEqual(v["first_invalid"], 1)

    def test_smart_attacker_breaks_next_link(self):
        chain = Blockchain()
        chain.add_block("CREDENTIAL_ISSUED", {"credential_id": "a", "credential_hash": "ab" * 32})
        chain.add_block("CREDENTIAL_ISSUED", {"credential_id": "b", "credential_hash": "cd" * 32})
        chain.simulate_tamper(1, recompute_hash=True)
        v = chain.validate()
        self.assertFalse(v["valid"])
        self.assertEqual(v["first_invalid"], 2)       # block 1 looks fine, block 2's link is broken

    def test_cannot_append_to_invalid_chain_and_restore_works(self):
        chain = Blockchain()
        chain.add_block("CREDENTIAL_ISSUED", {"credential_id": "a", "credential_hash": "ab" * 32})
        chain.simulate_tamper(1)
        with self.assertRaises(ChainError):
            chain.add_block("CREDENTIAL_ISSUED", {"credential_id": "c", "credential_hash": "ef" * 32})
        self.assertTrue(chain.restore_backup())
        self.assertTrue(chain.validate()["valid"])


if __name__ == "__main__":
    import unittest
    unittest.main()
