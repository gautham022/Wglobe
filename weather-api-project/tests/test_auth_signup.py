import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth_router import router as auth_router


class FakeResponse:
    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error


class FakeQuery:
    def __init__(self, data=None):
        self.data = data

    def eq(self, column, value):
        return self

    def execute(self):
        return FakeResponse(data=self.data)


class FakeTable:
    def __init__(self, rows=None):
        self.rows = rows or []

    def select(self, *args, **kwargs):
        return FakeQuery(self.rows)

    def insert(self, payload):
        self.payload = payload
        return FakeQuery([payload])


class FakeSupabaseClient:
    def __init__(self, existing_rows=None):
        self.existing_rows = existing_rows or []
        self.table_calls = []

    def table(self, name):
        self.table_calls.append(name)
        if name == "users":
            return FakeTable(self.existing_rows)
        raise AssertionError(f"Unexpected table: {name}")


class SignupRouterTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(auth_router)
        self.client = TestClient(self.app)

    def test_signup_creates_user_for_valid_payload(self):
        fake_client = FakeSupabaseClient(existing_rows=[])

        with patch("auth_router.get_supabase_client", return_value=fake_client):
            response = self.client.post(
                "/signup",
                json={"name": "Jane Doe", "email": "jane@example.com", "password": "StrongPass123"},
            )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["name"], "Jane Doe")
        self.assertEqual(body["email"], "jane@example.com")
        self.assertIn("password_hash", body)
        self.assertNotEqual(body["password_hash"], "StrongPass123")

    def test_signup_rejects_duplicate_email(self):
        fake_client = FakeSupabaseClient(existing_rows=[{"email": "jane@example.com"}])

        with patch("auth_router.get_supabase_client", return_value=fake_client):
            response = self.client.post(
                "/signup",
                json={"name": "Jane Doe", "email": "jane@example.com", "password": "StrongPass123"},
            )

        self.assertEqual(response.status_code, 409)
        self.assertIn("already exists", response.json()["detail"].lower())

    def test_signup_rejects_invalid_payload(self):
        response = self.client.post(
            "/signup",
            json={"name": "", "email": "not-an-email", "password": "123"},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
