import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUPPLIER_SITE = ROOT / "e2e" / "supplier-site"


class E2ESupportContractTest(unittest.TestCase):
    def test_e2e_env_keys_are_defined(self):
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        for key in [
            "WEBUI_BASE_URL",
            "API_BASE_URL",
            "TEST_SUPPLIER_SITE_URL",
            "TEST_SUPPLIER_EMAIL",
            "TEST_SUPPLIER_TELEGRAM",
            "BROWSER_PROVIDER",
            "BROWSER_MCP_SERVICE_NAME",
            "BROWSER_MCP_URL",
            "BROWSER_ALLOWED_DOMAINS",
            "EMAIL_CONNECTOR_PROVIDER",
            "EMAIL_SMTP_HOST",
            "TELEGRAM_CONNECTOR_PROVIDER",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHAT_ID",
            "MODEL_PROVIDER",
            "MODEL_NAME",
            "OLLAMA_BASE_URL",
            "WEB_SEARCH_PROVIDER",
            "WEB_SEARCH_URL",
        ]:
            with self.subTest(key=key):
                self.assertIn(f"{key}=", env_example)

    def test_controlled_supplier_site_contains_required_products(self):
        required_pages = {
            "products/e2e-uav-flight-controller-fc-100.html": "E2E UAV Flight Controller FC-100",
            "products/e2e-industrial-cnc-controller-ic-200.html": "E2E Industrial CNC Controller IC-200",
            "products/e2e-rack-workstation-rw-500.html": "E2E Rack Workstation RW-500",
            "products/invalid-products.html": "not-an-email",
            "products/e2e-email-failure.html": "failure@example.invalid",
            "products/e2e-telegram-failure.html": "@unreachable_supplier_e2e",
        }
        for relative_path, expected_text in required_pages.items():
            with self.subTest(page=relative_path):
                text = (SUPPLIER_SITE / relative_path).read_text(encoding="utf-8")
                self.assertIn(expected_text, text)

    def test_e2e_preflight_and_cleanup_exist(self):
        preflight = (ROOT / "scripts" / "e2e_preflight.py").read_text(encoding="utf-8")
        cleanup = (ROOT / "scripts" / "e2e_cleanup.sql").read_text(encoding="utf-8")

        self.assertIn("load_env_file", preflight)
        for key in [
            "WEBUI_BASE_URL",
            "API_BASE_URL",
            "POSTGRES_HOST",
            "WORKER_SERVICE_NAME",
            "BROWSER_MCP_URL",
            "EMAIL_SMTP_HOST",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHAT_ID",
        ]:
            with self.subTest(key=key):
                self.assertIn(key, preflight)

        self.assertIn("agent_tasks", cleanup)
        self.assertIn("contact_attempts", cleanup)
        self.assertIn("queued", cleanup)
        self.assertIn("running", cleanup)


if __name__ == "__main__":
    unittest.main()
