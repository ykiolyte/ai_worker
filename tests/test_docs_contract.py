import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class DocsContractTest(unittest.TestCase):
    def test_required_docs_exist(self):
        for name in ["development.md", "connectors.md", "mvp-limitations.md", "testing.md", "e2e-report-template.md"]:
            with self.subTest(name=name):
                self.assertTrue((DOCS / name).exists())

    def test_environment_and_startup_are_documented(self):
        development = (DOCS / "development.md").read_text(encoding="utf-8")
        for expected in ["DATABASE_URL", "REDIS_URL", "MODEL_PROVIDER", "docker compose up --build", "openspec.cmd"]:
            with self.subTest(expected=expected):
                self.assertIn(expected, development)

    def test_connectors_and_limits_are_documented(self):
        connectors = (DOCS / "connectors.md").read_text(encoding="utf-8")
        limits = (DOCS / "mvp-limitations.md").read_text(encoding="utf-8")
        for expected in ["BrowserMcpConnector", "EmailConnector", "TelegramConnector"]:
            self.assertIn(expected, connectors)
        for forbidden in ["autonomous purchasing", "payments", "mass messaging", "advanced CRM"]:
            self.assertIn(forbidden, limits)

    def test_gmail_smtp_configuration_is_documented(self):
        connectors = (DOCS / "connectors.md").read_text(encoding="utf-8")
        development = (DOCS / "development.md").read_text(encoding="utf-8")
        for expected in ["smtp.gmail.com", "Gmail app password", "EMAIL_SMTP_PASSWORD"]:
            with self.subTest(expected=expected):
                self.assertIn(expected, connectors)
        self.assertIn("AUTO_PROCESS_SUPPLIER_CONTACT_TASKS", development)

    def test_multi_engine_web_search_configuration_is_documented(self):
        connectors = (DOCS / "connectors.md").read_text(encoding="utf-8")
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        for expected in ["WEB_SEARCH_PROVIDER=multi", "WEB_SEARCH_ENGINES", "duckduckgo", "searxng"]:
            with self.subTest(expected=expected):
                self.assertIn(expected, connectors)
                self.assertIn(expected, env_example)

    def test_testing_doc_covers_tdd_and_protocol(self):
        testing = (DOCS / "testing.md").read_text(encoding="utf-8")
        for expected in ["red", "green", "refactor", "test_protocol.md", "python -m unittest discover -s tests"]:
            self.assertIn(expected, testing)

    def test_report_template_lists_acceptance_case(self):
        report = (DOCS / "e2e-report-template.md").read_text(encoding="utf-8")
        self.assertIn("TC-E2E-ACCEPTANCE-001", report)
        self.assertIn("MVP принят / MVP не принят", report)


if __name__ == "__main__":
    unittest.main()
