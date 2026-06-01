import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.config import Settings


class SettingsEnvFileContractTest(unittest.TestCase):
    def test_settings_loads_local_env_file_without_exported_variables(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "AUTO_PROCESS_SEARCH_TASKS=true\n"
                "AUTO_PROCESS_SUPPLIER_CONTACT_TASKS=true\n"
                "SEARCH_CONTACT_ENRICHMENT_PAGES=1\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"LOAD_DOTENV_IN_TESTS": "true"}, clear=True), patch("os.getcwd", return_value=tmp):
                settings = Settings.from_env()

        self.assertTrue(settings.auto_process_search_tasks)
        self.assertTrue(settings.auto_process_supplier_contact_tasks)
        self.assertEqual(1, settings.search_contact_enrichment_pages)

    def test_settings_loads_made_in_china_connector_options(self):
        with patch.dict(
            os.environ,
            {
                "MADE_IN_CHINA_DISCOVERY_ENABLED": "true",
                "MADE_IN_CHINA_BASE_URL": "https://example.test/products-search/hot-china-products",
                "MADE_IN_CHINA_TIMEOUT_SECONDS": "9",
                "MADE_IN_CHINA_MAX_RESULTS": "4",
            },
            clear=True,
        ):
            settings = Settings.from_env()

        self.assertTrue(settings.made_in_china_discovery_enabled)
        self.assertEqual("https://example.test/products-search/hot-china-products", settings.made_in_china_base_url)
        self.assertEqual(9, settings.made_in_china_timeout_seconds)
        self.assertEqual(4, settings.made_in_china_max_results)

    def test_settings_loads_public_search_provider_options(self):
        with patch.dict(
            os.environ,
            {
                "ENABLE_MADE_IN_CHINA_PROVIDER": "true",
                "MADE_IN_CHINA_PROVIDER_MAX_RESULTS": "20",
                "MADE_IN_CHINA_PROVIDER_RATE_LIMIT_SECONDS": "3",
                "SEARCH_PROVIDER_ORDER": "made_in_china_public,generic_web,browser_mcp",
            },
            clear=True,
        ):
            settings = Settings.from_env()

        self.assertTrue(settings.enable_made_in_china_provider)
        self.assertEqual(20, settings.made_in_china_provider_max_results)
        self.assertEqual(3.0, settings.made_in_china_provider_rate_limit_seconds)
        self.assertEqual("made_in_china_public,generic_web,browser_mcp", settings.search_provider_order)
