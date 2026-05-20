from __future__ import annotations

import os
import time

from .agent import AgentRuntime
from .config import Settings
from .connectors import build_tool_registry
from .domain import AgentTaskStatus, AgentTaskType
from .model_providers import LocalDemoModelProvider, OllamaModelProvider
from .repositories import InMemoryRepository
from .workers import process_contract_draft, process_product_search, process_supplier_contact


class ConfiguredWorkerModelProvider:
    def __init__(self, provider: str, model_name: str) -> None:
        self.provider = provider
        self.model_name = model_name
        self.name = f"{provider}:{model_name}" if provider and model_name else "unconfigured-model"

    def complete(self, prompt: str, tools=None):
        raise RuntimeError("configured model provider is not wired for worker completions yet")


def run_worker_tick(
    repo: InMemoryRepository,
    runtime: AgentRuntime,
    allow_products_without_contacts: bool = False,
    max_tasks: int | None = None,
) -> int:
    processed = 0
    for task in sorted(repo.agent_tasks.values(), key=lambda item: item.created_at):
        if task.status != AgentTaskStatus.QUEUED:
            continue
        if max_tasks is not None and processed >= max_tasks:
            break
        if task.task_type == AgentTaskType.PRODUCT_SEARCH:
            process_product_search(repo, runtime, task.id, allow_products_without_contacts)
        elif task.task_type == AgentTaskType.SUPPLIER_CONTACT:
            process_supplier_contact(repo, runtime, task.id)
        elif task.task_type == AgentTaskType.CONTRACT_DRAFT:
            process_contract_draft(repo, runtime, task.id)
        else:
            continue
        processed += 1
    return processed


def run_worker_loop(
    repo: InMemoryRepository,
    runtime: AgentRuntime,
    allow_products_without_contacts: bool = False,
    poll_interval_seconds: float = 5,
    max_ticks: int | None = None,
    max_tasks_per_tick: int | None = None,
) -> int:
    processed = 0
    ticks = 0
    while max_ticks is None or ticks < max_ticks:
        ticks += 1
        processed += run_worker_tick(
            repo,
            runtime,
            allow_products_without_contacts=allow_products_without_contacts,
            max_tasks=max_tasks_per_tick,
        )
        if poll_interval_seconds > 0:
            time.sleep(poll_interval_seconds)
    return processed


def run_idle_worker(poll_interval_seconds: float, max_ticks: int | None = None) -> int:
    ticks = 0
    while max_ticks is None or ticks < max_ticks:
        ticks += 1
        if poll_interval_seconds > 0:
            time.sleep(poll_interval_seconds)
    return ticks


def build_worker_runtime(settings: Settings) -> AgentRuntime:
    model_provider = build_worker_model_provider(settings)
    return AgentRuntime(
        model_provider=model_provider,
        tool_registry=build_tool_registry(settings, model_provider),
    )


def build_worker_model_provider(settings: Settings):
    provider = settings.model_provider.strip().lower()
    if provider == "local_demo":
        return LocalDemoModelProvider(name=f"local_demo:{settings.model_name or 'browser-extraction-v0'}")
    if provider == "ollama":
        return OllamaModelProvider(
            base_url=settings.ollama_base_url,
            model_name=settings.model_name,
            timeout_seconds=settings.ollama_timeout_seconds,
        )
    return ConfiguredWorkerModelProvider(settings.model_provider, settings.model_name)


def main() -> None:
    settings = Settings.from_env()
    repo = InMemoryRepository()
    runtime = build_worker_runtime(settings)
    poll_interval = float(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "5"))
    max_tasks_per_tick = int(os.getenv("WORKER_MAX_TASKS_PER_TICK", "10"))
    run_worker_loop(
        repo,
        runtime,
        allow_products_without_contacts=settings.allow_products_without_contacts,
        poll_interval_seconds=poll_interval,
        max_tasks_per_tick=max_tasks_per_tick,
    )


if __name__ == "__main__":
    main()
