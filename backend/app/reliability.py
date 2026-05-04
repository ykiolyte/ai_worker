from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import time
from typing import Callable, TypeVar

from .domain import AgentTaskStatus, ContactAttemptStatus
from .repositories import InMemoryRepository


T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 0.25

    def run(self, action: Callable[[], T]) -> T:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return action()
            except Exception as exc:
                last_error = exc
                if attempt < self.max_attempts and self.backoff_seconds > 0:
                    time.sleep(self.backoff_seconds)
        raise last_error or RuntimeError("retry policy failed without an error")


def recover_timed_out_work(repo: InMemoryRepository, timeout_seconds: int) -> int:
    recovered = 0
    now = datetime.now(timezone.utc)

    for task in repo.agent_tasks.values():
        if task.status not in {AgentTaskStatus.QUEUED, AgentTaskStatus.RUNNING}:
            continue
        anchor = task.started_at or task.created_at
        if (now - anchor).total_seconds() <= timeout_seconds:
            continue
        task.error_message = "agent task timed out"
        if task.status == AgentTaskStatus.QUEUED:
            task.transition_to(AgentTaskStatus.RUNNING)
        task.transition_to(AgentTaskStatus.FAILED)
        recovered += 1

    for attempt in repo.contact_attempts.values():
        if attempt.status not in {ContactAttemptStatus.QUEUED, ContactAttemptStatus.RUNNING}:
            continue
        anchor = attempt.sent_at or attempt.created_at
        if (now - anchor).total_seconds() <= timeout_seconds:
            continue
        attempt.error_message = "contact attempt timed out"
        if attempt.status == ContactAttemptStatus.QUEUED:
            attempt.transition_to(ContactAttemptStatus.RUNNING)
        attempt.transition_to(ContactAttemptStatus.FAILED)
        recovered += 1

    return recovered

