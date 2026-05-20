import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SetupContractTest(unittest.TestCase):
    def test_required_setup_files_exist(self):
        required = [
            "backend/pyproject.toml",
            "backend/app/__init__.py",
            "backend/app/config.py",
            "backend/app/database.py",
            "backend/app/broker.py",
            "backend/app/main.py",
            "frontend/package.json",
            "frontend/tsconfig.json",
            "frontend/vite.config.ts",
            "frontend/src/App.tsx",
            "frontend/src/main.tsx",
            "docker-compose.yml",
            "docs/development.md",
        ]

        missing = [path for path in required if not (ROOT / path).exists()]
        self.assertEqual([], missing, f"Missing setup files: {missing}")

    def test_env_example_covers_runtime_and_e2e(self):
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        required_keys = [
            "WEBUI_BASE_URL",
            "API_BASE_URL",
            "DATABASE_URL",
            "POSTGRES_HOST",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "REDIS_URL",
            "WORKER_SERVICE_NAME",
            "AUTO_PROCESS_SUPPLIER_CONTACT_TASKS",
            "BROWSER_PROVIDER",
            "BROWSER_MCP_SERVICE_NAME",
            "BROWSER_MCP_URL",
            "BROWSER_MCP_COMMAND",
            "BROWSER_MCP_ARGS",
            "BROWSER_ALLOWED_DOMAINS",
            "BROWSER_RESEARCH_MODE",
            "BROWSER_ALLOW_PUBLIC_INTERNET",
            "INTERNET_SEARCH_URL_TEMPLATE",
            "INTERNET_SEARCH_RESULT_LIMIT",
            "ALLOW_PRODUCTS_WITHOUT_CONTACTS",
            "EMAIL_CONNECTOR_PROVIDER",
            "EMAIL_SMTP_HOST",
            "EMAIL_USE_TLS",
            "EMAIL_USE_SSL",
            "AUTO_SYNC_GMAIL_INBOUND",
            "GMAIL_INBOUND_SYNC_INTERVAL_SECONDS",
            "TELEGRAM_CONNECTOR_PROVIDER",
            "TELEGRAM_BOT_TOKEN",
            "MODEL_PROVIDER",
            "MODEL_NAME",
            "OLLAMA_BASE_URL",
            "OLLAMA_TIMEOUT_SECONDS",
            "WEB_SEARCH_PROVIDER",
            "WEB_SEARCH_URL",
            "WEB_SEARCH_RESULT_LIMIT",
            "AI_SEARCH_QUERY_COUNT",
            "AI_SEARCH_CANDIDATE_LIMIT",
            "SEARCH_CONTACT_ENRICHMENT_PAGES",
            "TEST_SUPPLIER_SITE_URL",
            "TEST_SUPPLIER_EMAIL",
            "TEST_SUPPLIER_TELEGRAM",
        ]

        missing = [key for key in required_keys if f"{key}=" not in env_example]
        self.assertEqual([], missing, f"Missing env keys: {missing}")

    def test_docker_compose_defines_core_services(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        for service_name in [
            "postgres",
            "redis",
            "backend",
            "worker",
            "webui",
            "browser-mcp",
            "searxng",
            "ollama",
            "mailpit",
        ]:
            with self.subTest(service_name=service_name):
                self.assertIn(f"  {service_name}:", compose)

    def test_backend_image_includes_company_knowledge_document(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("context: .", compose)
        self.assertIn("dockerfile: backend/Dockerfile", compose)
        self.assertIn("COPY docs/ooo.md /app/docs/ooo.md", dockerfile)

    def test_backend_starts_gmail_inbound_background_sync(self):
        main = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
        workers = (ROOT / "backend" / "app" / "workers.py").read_text(encoding="utf-8")

        self.assertIn("start_gmail_inbound_sync_loop", main)
        self.assertIn("run_gmail_inbound_sync_loop", main)
        self.assertIn("_gmail_sync_lock", workers)

    def test_compose_allows_real_browser_target_from_env(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("${DOCKER_TEST_SUPPLIER_SITE_URL:-http://supplier-site}", compose)
        self.assertIn("${DOCKER_BROWSER_ALLOWED_DOMAINS:-supplier-site,localhost,127.0.0.1}", compose)

    def test_frontend_container_includes_vite_and_typescript_config(self):
        dockerfile = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("vite.config.ts", dockerfile)
        self.assertIn("tsconfig.json", dockerfile)


if __name__ == "__main__":
    unittest.main()
