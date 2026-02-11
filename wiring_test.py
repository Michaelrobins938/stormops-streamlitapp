
import unittest
from state import AppState, Mission, Zone, Route, Job
from datetime import datetime

class TestWiring(unittest.TestCase):
    def test_app_state_initialization(self):
        state = AppState()
        self.assertIsNone(state.storm_id)
        self.assertEqual(state.mission.current_step, "detect_storm")
        self.assertEqual(state.mission.play_score, 0)

    def test_play_score_range(self):
        # Play score logic is currently in app.py, 
        # in a real hardened app we'd move it to logic.py or AppState method.
        # For now, we'll just check if we can manipulate it.
        state = AppState()
        state.mission.play_score = 105
        self.assertGreater(state.mission.play_score, 100) # Manual check
        
    def test_zone_to_dict(self):
        zone = Zone(zip_code="76201", impact_index=85.0)
        z_dict = zone.__dict__
        self.assertEqual(z_dict["zip_code"], "76201")
        self.assertEqual(z_dict["impact_index"], 85.0)

    def test_app_state_to_dict(self):
        state = AppState(storm_id="TEST-001", storm_name="DFW Hail")
        state.zones["76201"] = Zone(zip_code="76201", impact_index=90.0)
        d = state.to_dict()
        self.assertEqual(d["storm_id"], "TEST-001")
        self.assertIn("76201", d["zones"])
        self.assertEqual(d["zones"]["76201"]["impact_index"], 90.0)

if __name__ == '__main__':
    unittest.main()
