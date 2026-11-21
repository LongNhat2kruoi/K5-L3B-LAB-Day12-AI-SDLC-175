"""Tests for the one-session day mode: gather in the morning, quan at night."""

import unittest

from chonoi.contract import load_contract
from chonoi.inputs import LiveInputs
from chonoi.runner import Session
from helpers import Workdir, events, read_jsonl, run_headless, snapshots, write_json


class DayMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tuning = load_contract()["tuning"]

    @staticmethod
    def names(rows):
        return [row["name"] for row in rows]

    def test_gather_inventory_transitions_to_quan_in_same_session(self):
        scenario = {
            "gather": {"hold": ["ca_loc"], "time_left_ticks": 1},
            "quan": {"random_customers": False, "time_left_ticks": 1},
        }
        session = Session("day", self.tuning, scenario, seed=1)

        initial = session.snapshot()
        self.assertEqual((initial["mode"], initial["phase"], initial["phase_tick"]), ("day", "gather", 0))

        rows = session.step(LiveInputs().advance())

        self.assertEqual(self.names(rows), ["gather_end", "phase_changed"])
        self.assertEqual(rows[0]["phase"], "gather")
        self.assertEqual(rows[1]["phase"], "quan")
        night = session.snapshot()
        self.assertEqual((night["mode"], night["phase"], night["phase_tick"]), ("day", "quan", 0))
        self.assertEqual(night["stock"], {"ca_loc": 1})
        self.assertEqual(rows[1]["data"]["inventory"], {"items": {"ca_loc": 1}})

    def test_day_finishes_after_night_and_uses_day_end_row(self):
        scenario = {
            "gather": {"hold": ["ca_loc"], "time_left_ticks": 1},
            "quan": {"random_customers": False, "time_left_ticks": 1},
        }
        session = Session("day", self.tuning, scenario, seed=1)
        session.step(LiveInputs().advance())
        rows = session.step(LiveInputs().advance())

        self.assertEqual(self.names(rows), ["quan_end"])
        self.assertTrue(session.done)
        end = session.end_row()
        self.assertEqual((end["mode"], end["reason"], end["ticks"], end["sim_tick"]),
                         ("day", "time", 2, 2))

    def test_day_is_deterministic_for_same_seed_and_input(self):
        scenario = {
            "gather": {"hold": ["ca_loc"], "time_left_ticks": 2},
            "quan": {"random_customers": False, "time_left_ticks": 2},
        }
        a = Session("day", self.tuning, scenario, seed=7)
        b = Session("day", self.tuning, scenario, seed=7)
        inputs = [LiveInputs().advance(), LiveInputs().advance(), LiveInputs().advance()]
        for inp in inputs:
            self.assertEqual(a.step(inp), b.step(inp))
            self.assertEqual(a.snapshot(), b.snapshot())

    def test_headless_day_accepts_composite_scenario(self):
        scenario = {
            "gather": {"hold": ["ca_loc"], "time_left_ticks": 1},
            "quan": {"random_customers": False, "time_left_ticks": 1},
        }
        with Workdir() as work:
            scenario_path = write_json(work.path("day.json"), scenario)
            output_path = work.path("day.jsonl")
            code, err = run_headless("--mode", "day", "--seed", "1", "--ticks", "2",
                                     "--scenario", scenario_path, "--out", output_path)
            self.assertEqual(code, 0, err)
            rows = read_jsonl(output_path)
            self.assertEqual(snapshots(rows)[0]["phase"], "gather")
            self.assertEqual(snapshots(rows)[-1]["phase"], "quan")
            self.assertEqual(events(rows, "phase_changed")[0]["data"]["to"], "quan")
            self.assertEqual(rows[-1]["mode"], "day")


if __name__ == "__main__":
    unittest.main()
