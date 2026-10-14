import json
from tests.base import TempDataTestCase


class ApiTests(TempDataTestCase):
    def setUp(self):
        super().setUp()
        from app import create_app
        self.client = create_app().test_client()

    def post(self, url, payload=None):
        return self.client.post(url, json=payload or {})

    def test_full_flow(self):
        issuer = self.post("/api/identity/create", {"name": "Uni", "role": "issuer"}).get_json()
        self.assertTrue(issuer["success"])
        r = self.post("/api/credential/issue", {"issuer_did": issuer["did"], "name": "Rahul",
                      "student_id": "CS101", "department": "CSE", "course": "Crypto"}).get_json()
        cred = r["credential"]
        v = self.post("/api/credential/verify", {"credential": cred}).get_json()
        self.assertTrue(v["valid"])
        cred["subject"]["student_id"] = "CS999"
        v = self.post("/api/credential/verify", {"credential": json.dumps(cred)}).get_json()
        self.assertFalse(v["valid"])

    def test_bad_input_returns_error_json(self):
        r = self.post("/api/identity/create", {"name": "", "role": "holder"})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.get_json()["success"])
        r = self.post("/api/credential/verify", {"credential": "{oops"})
        self.assertFalse(r.get_json()["success"])

    def test_pages_render(self):
        self.post("/api/demo/seed")
        for url in ("/", "/create-identity", "/identities", "/issue-credential",
                    "/credentials", "/verify", "/blockchain"):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_private_keys_are_not_served(self):
        self.post("/api/demo/seed")
        self.assertEqual(self.client.get("/data/identities/x/private_key.pem").status_code, 404)
        self.assertEqual(self.client.get("/static/../data/identities").status_code, 404)

    def test_tamper_and_restore_endpoints(self):
        self.post("/api/demo/seed")
        self.post("/api/blockchain/tamper", {"index": 3})
        self.assertFalse(self.client.get("/api/blockchain/validate").get_json()["valid"])
        blocked = self.post("/api/identity/create", {"name": "X", "role": "holder"})
        self.assertEqual(blocked.status_code, 409)
        self.post("/api/blockchain/restore")
        self.assertTrue(self.client.get("/api/blockchain/validate").get_json()["valid"])


if __name__ == "__main__":
    import unittest
    unittest.main()
