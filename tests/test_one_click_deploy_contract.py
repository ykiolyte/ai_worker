import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OneClickDeployContractTest(unittest.TestCase):
    def test_root_launchers_delegate_to_powershell_bootstrap(self):
        start = ROOT / "START_PROJECT.cmd"
        stop = ROOT / "STOP_PROJECT.cmd"

        self.assertTrue(start.exists(), "START_PROJECT.cmd must exist at repo root")
        self.assertTrue(stop.exists(), "STOP_PROJECT.cmd must exist at repo root")

        start_text = start.read_text(encoding="utf-8")
        stop_text = stop.read_text(encoding="utf-8")

        for expected in ["powershell.exe", "-ExecutionPolicy", "Bypass", "scripts\\bootstrap-workstation.ps1", "%*"]:
            with self.subTest(file="START_PROJECT.cmd", expected=expected):
                self.assertIn(expected, start_text)

        for expected in ["powershell.exe", "-ExecutionPolicy", "Bypass", "scripts\\stop-project.ps1", "%*"]:
            with self.subTest(file="STOP_PROJECT.cmd", expected=expected):
                self.assertIn(expected, stop_text)

    def test_bootstrap_script_covers_env_model_compose_and_health_checks(self):
        script_path = ROOT / "scripts" / "bootstrap-workstation.ps1"
        self.assertTrue(script_path.exists(), "bootstrap-workstation.ps1 must exist")

        script = script_path.read_text(encoding="utf-8")
        expected_fragments = [
            "[switch]$DryRun",
            "[switch]$NoOpen",
            "[string]$ModelName",
            ".env.example",
            "Copy-Item",
            "Keeping existing .env",
            "install-ollama-portable.ps1",
            "start-ollama-local.ps1",
            "pull-local-model.ps1",
            "docker compose up --build -d",
            "http://127.0.0.1:8000/health",
            "http://127.0.0.1:5173",
            "Start-Process",
            "Docker Desktop",
        ]

        for expected in expected_fragments:
            with self.subTest(expected=expected):
                self.assertIn(expected, script)

    def test_stop_script_preserves_persistent_data(self):
        script_path = ROOT / "scripts" / "stop-project.ps1"
        self.assertTrue(script_path.exists(), "stop-project.ps1 must exist")

        script = script_path.read_text(encoding="utf-8")

        self.assertIn("docker compose down", script)
        self.assertIn("[switch]$DryRun", script)
        self.assertNotIn("down -v", script)
        self.assertNotIn("--volumes", script)

    def test_deployment_docs_cover_new_workstation_and_secrets(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        guide_path = ROOT / "docs" / "one-click-deploy.md"
        self.assertTrue(guide_path.exists(), "docs/one-click-deploy.md must exist")
        guide = guide_path.read_text(encoding="utf-8")
        combined = f"{readme}\n{guide}"

        expected_fragments = [
            "https://github.com/ykiolyte/ai_worker.git",
            "START_PROJECT.cmd",
            "STOP_PROJECT.cmd",
            "Docker Desktop",
            "mistral-nemo:12b",
            "Mailpit",
            "Gmail",
            "EMAIL_SMTP_PASSWORD",
            "EMAIL_IMAP_PASSWORD",
            "TELEGRAM_BOT_TOKEN",
            "docker compose logs",
        ]

        for expected in expected_fragments:
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)


if __name__ == "__main__":
    unittest.main()
