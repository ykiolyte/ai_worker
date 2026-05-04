from __future__ import annotations

import os
import time


def run_idle_worker(poll_interval_seconds: float, max_ticks: int | None = None) -> int:
    ticks = 0
    while max_ticks is None or ticks < max_ticks:
        ticks += 1
        if poll_interval_seconds > 0:
            time.sleep(poll_interval_seconds)
    return ticks


def main() -> None:
    poll_interval = float(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "5"))
    run_idle_worker(poll_interval_seconds=poll_interval)


if __name__ == "__main__":
    main()
