"""Bootstrap checks only; no lifespan hooks or database connections are run."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError


# Deliberately synthetic configuration, independent from any local .env file.
with patch.dict(os.environ, {
    "DATABASE_URL": "mysql+pymysql://test_user:test_password@127.0.0.1:1/test_bootstrap",
    "SECRET_KEY": "bootstrap-tests-only-not-a-deployment-secret",
    "DEBUG": "false",
}):
    from app.config import Settings
    from app.main import app


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        # No context manager: these checks must not seed a real database.
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_health_and_homepage(self):
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        homepage = self.client.get("/")
        self.assertEqual(homepage.status_code, 200)
        self.assertIn("校园在线", homepage.text)
        self.assertIn("text/html", homepage.headers["content-type"])

    def test_unknown_api_is_not_success_or_spa(self):
        for path in ("/api", "/api/v1/does-not-exist"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), {"detail": "Not Found"})

    def test_spa_fallback_does_not_serve_backend_source(self):
        response = self.client.get("/app/config.py")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertNotIn("class Settings", response.text)
        response = self.client.get("/static/%2e%2e/app/config.py")
        self.assertEqual(response.status_code, 404)

    def test_configuration_requires_secret_and_mysql_driver(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValidationError):
                Settings(_env_file=None)
            with self.assertRaises(ValidationError):
                Settings(_env_file=None, database_url="sqlite:///example.db", secret_key="x" * 40)
            with self.assertRaises(ValidationError):
                Settings(_env_file=None, database_url="mysql+pymysql://u:p@localhost/db", secret_key="short")
            settings = Settings(
                _env_file=None,
                database_url="mysql+pymysql://u:p@localhost/db",
                secret_key="x" * 40,
            )
            self.assertFalse(settings.debug)
            self.assertEqual(settings.app_name, "校园在线学习平台")


if __name__ == "__main__":
    unittest.main()
