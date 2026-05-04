from datetime import timedelta
import unittest

from backend.app.domain import (
    AgentTask,
    AgentTaskStatus,
    AgentTaskType,
    ContactAttempt,
    ContactAttemptStatus,
    ContactType,
)
from backend.app.observability import build_log_event, public_error_message, redact_secrets
from backend.app.reliability import RetryPolicy, recover_timed_out_work
from backend.app.repositories import InMemoryRepository


class ObservabilityContractTest(unittest.TestCase):
    def test_structured_log_event_contains_correlation_ids(self):
        event = build_log_event(
            task_type="product_search",
            status="completed",
            duration_ms=42,
            agent_task_id="agent-1",
            search_request_id="search-1",
            product_id="product-1",
            contact_attempt_id="contact-1",
        )

        self.assertEqual("agent-1", event["agent_task_id"])
        self.assertEqual("search-1", event["search_request_id"])
        self.assertEqual("product-1", event["product_id"])
        self.assertEqual("contact-1", event["contact_attempt_id"])
        self.assertEqual(42, event["duration_ms"])

    def test_secret_redaction(self):
        payload = {
            "SMTP_PASSWORD": "secret",
            "TELEGRAM_BOT_TOKEN": "token",
            "nested": {"api_key": "key", "safe": "visible"},
        }

        redacted = redact_secrets(payload)

        self.assertEqual("***REDACTED***", redacted["SMTP_PASSWORD"])
        self.assertEqual("***REDACTED***", redacted["TELEGRAM_BOT_TOKEN"])
        self.assertEqual("***REDACTED***", redacted["nested"]["api_key"])
        self.assertEqual("visible", redacted["nested"]["safe"])

    def test_public_error_message_hides_developer_details(self):
        message = public_error_message(RuntimeError("SMTP_PASSWORD=secret traceback detail"))
        self.assertNotIn("SMTP_PASSWORD", message)
        self.assertNotIn("traceback", message.lower())
        self.assertIn("Не удалось выполнить операцию", message)


class ReliabilityContractTest(unittest.TestCase):
    def test_retry_policy_retries_until_success(self):
        attempts = []

        def flaky():
            attempts.append("try")
            if len(attempts) < 3:
                raise RuntimeError("temporary")
            return "ok"

        result = RetryPolicy(max_attempts=3, backoff_seconds=0).run(flaky)

        self.assertEqual("ok", result)
        self.assertEqual(3, len(attempts))

    def test_timeout_recovery_fails_active_tasks_and_attempts(self):
        repo = InMemoryRepository()
        task = repo.add_agent_task(AgentTask.create(AgentTaskType.PRODUCT_SEARCH, {}))
        task.created_at = task.created_at - timedelta(hours=1)
        attempt = repo.add_contact_attempt(
            ContactAttempt.create(task.id, task.id, ContactType.EMAIL, "message")
        )
        attempt.created_at = attempt.created_at - timedelta(hours=1)

        recovered = recover_timed_out_work(repo, timeout_seconds=60)

        self.assertEqual(2, recovered)
        self.assertEqual(AgentTaskStatus.FAILED, task.status)
        self.assertEqual(ContactAttemptStatus.FAILED, attempt.status)
        self.assertIn("timed out", task.error_message)
        self.assertIn("timed out", attempt.error_message)


if __name__ == "__main__":
    unittest.main()
