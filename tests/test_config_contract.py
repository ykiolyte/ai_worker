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
