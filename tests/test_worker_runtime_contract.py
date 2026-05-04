import unittest

from backend.app.worker import run_idle_worker


class WorkerRuntimeContractTest(unittest.TestCase):
    def test_idle_worker_can_run_one_tick_without_crashing(self):
        ticks = run_idle_worker(poll_interval_seconds=0, max_ticks=1)

        self.assertEqual(1, ticks)


if __name__ == "__main__":
    unittest.main()
