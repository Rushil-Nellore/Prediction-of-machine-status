from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from predictive_maintenance.data.simulate import generate_dataset
from predictive_maintenance.data.external import import_ai4i_dataset
from predictive_maintenance.realtime import PredictiveMaintenanceEngine
from predictive_maintenance.training import train_model


class SmokeTest(unittest.TestCase):
    def test_bootstrap_and_realtime_engine(self) -> None:
        generate_dataset(hours=720)
        train_model()
        engine = PredictiveMaintenanceEngine()
        summary = engine.fleet_summary()
        self.assertGreater(summary["machine_count"], 0)
        self.assertIn("average_health", summary)
        snapshot = engine.tick()
        self.assertTrue(snapshot)
        baseline_health = engine.latest_by_machine["MX-101"]["health_score"]
        engine.trigger_scenario("MX-101", "overheating")
        scenario_health = engine.latest_by_machine["MX-101"]["health_score"]
        self.assertLess(scenario_health, baseline_health)
        self.assertIsNotNone(engine.latest_by_machine["MX-101"]["scenario"])
        added = engine.add_machine(
            "MX-201",
            "MX-101",
            {
                "vibration": 2.25,
                "temperature": 61.0,
                "pressure": 30.5,
                "current": 15.8,
                "rpm": 1460.0,
                "load": 57.0,
            },
        )
        self.assertEqual(added["current"]["machine_id"], "MX-201")
        self.assertIn("MX-201", engine.machine_ids)
        removed = engine.remove_machine("MX-201")
        self.assertEqual(removed["removed_machine_id"], "MX-201")
        self.assertNotIn("MX-201", engine.machine_ids)

    def test_ai4i_import_and_training(self) -> None:
        import_ai4i_dataset()
        train_model()
        engine = PredictiveMaintenanceEngine()
        self.assertTrue(any(machine_id.startswith("AI4I-") for machine_id in engine.machine_ids))
        self.assertGreater(engine.fleet_summary()["machine_count"], 0)


if __name__ == "__main__":
    unittest.main()
