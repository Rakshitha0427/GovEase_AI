import unittest
from unittest.mock import AsyncMock, patch

import mongomock
import pymupdf
from fastapi.testclient import TestClient

from backend.database import ensure_indexes, get_database
from backend.main import app


class AccountFeatureTests(unittest.TestCase):
    def setUp(self):
        self.mongo = mongomock.MongoClient(tz_aware=True)
        self.db = self.mongo["govease_test"]
        ensure_indexes(self.db)
        app.dependency_overrides[get_database] = lambda: self.db
        app.state.database_provider = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        app.state.database_provider = get_database
        self.mongo.close()

    def signup(self, client, email="citizen@example.com", name="Asha Citizen"):
        return client.post("/api/auth/signup", json={"name": name, "email": email, "password": "a-strong-test-password"})

    def test_signup_login_and_logout(self):
        response = self.signup(self.client)
        self.assertEqual(response.status_code, 201)
        account = response.json()
        self.assertEqual(account["email"], "citizen@example.com")
        self.assertNotIn("password", account)
        stored = self.db.users.find_one({"email_normalized": "citizen@example.com"})
        self.assertNotEqual(stored["password_hash"], "a-strong-test-password")
        self.assertTrue(stored["password_hash"].startswith("scrypt$"))

        self.client.post("/api/auth/logout")
        login = self.client.post("/api/auth/login", json={"email": "CITIZEN@example.com", "password": "a-strong-test-password"})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").json()["id"], account["id"])
        self.client.post("/api/auth/logout")
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_profile_update(self):
        self.assertEqual(self.signup(self.client).status_code, 201)
        updated = self.client.patch("/api/auth/profile", json={"name": "Asha Rao", "email": "asha.rao@example.com"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Asha Rao")
        self.assertEqual(self.client.get("/api/auth/me").json()["email"], "asha.rao@example.com")

    def test_conversation_history_rename_delete_and_user_isolation(self):
        self.assertEqual(self.signup(self.client).status_code, 201)
        other = TestClient(app)
        self.assertEqual(self.signup(other, "other@example.com", "Other Citizen").status_code, 201)
        try:
            with patch("backend.main.gemini_answer", new=AsyncMock(return_value="A helpful answer.")):
                sent = self.client.post("/api/chat", json={"message": "Find scholarships for students", "language": "English", "history": []})
                self.assertEqual(sent.status_code, 200)
                conversation_id = sent.json()["conversation_id"]
                self.assertTrue(conversation_id)
                continued = self.client.post("/api/chat", json={"message": "What documents could be required?", "language": "English", "history": [{"role": "user", "content": "Find scholarships for students"}, {"role": "assistant", "content": "A helpful answer."}], "conversation_id": conversation_id})
            self.assertEqual(continued.status_code, 200)
            self.assertEqual(continued.json()["conversation_id"], conversation_id)

            listing = self.client.get("/api/conversations")
            self.assertEqual(listing.status_code, 200)
            self.assertEqual(listing.json()[0]["id"], conversation_id)
            detail = self.client.get(f"/api/conversations/{conversation_id}")
            self.assertEqual(detail.status_code, 200)
            self.assertEqual([m["role"] for m in detail.json()["messages"]], ["user", "assistant", "user", "assistant"])

            self.assertEqual(other.get(f"/api/conversations/{conversation_id}").status_code, 404)
            self.assertEqual(other.patch(f"/api/conversations/{conversation_id}", json={"title": "Private"}).status_code, 404)
            self.assertEqual(other.delete(f"/api/conversations/{conversation_id}").status_code, 404)

            renamed = self.client.patch(f"/api/conversations/{conversation_id}", json={"title": "Scholarships"})
            self.assertEqual(renamed.json()["title"], "Scholarships")
            self.assertEqual(self.client.delete(f"/api/conversations/{conversation_id}").status_code, 204)
            self.assertEqual(self.client.get("/api/conversations").json(), [])
        finally:
            other.close()

    def test_guest_chat_does_not_require_database(self):
        app.state.database_provider = lambda: (_ for _ in ()).throw(AssertionError("guest chat should not touch MongoDB"))
        with patch("backend.main.gemini_answer", new=AsyncMock(return_value="Guest answer.")):
            response = self.client.post("/api/chat", json={"message": "Hello", "language": "English", "history": []})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["conversation_id"])

    def test_pdf_extraction_still_works(self):
        pdf = pymupdf.open()
        page = pdf.new_page()
        page.insert_text((72, 72), "A scholarship application needs an income certificate.")
        content = pdf.tobytes()
        pdf.close()
        response = self.client.post("/api/documents", files={"file": ("notice.pdf", content, "application/pdf")})
        self.assertEqual(response.status_code, 200)
        self.assertIn("income certificate", response.json()["text"])


if __name__ == "__main__":
    unittest.main()
