"""Unit tests for Gather survival rules owned by member 1."""

import unittest

from chonoi.contract import load_contract
from chonoi.inputs import LiveInputs
from chonoi.runner import Session


class GatherSurvival(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tuning = load_contract()["tuning"]

    def make_session(self, player=None, hold=None):
        block = {"player": player or {}}
        if hold is not None:
            block["hold"] = hold
        return Session("gather", self.tuning, block, seed=1)

    @staticmethod
    def step(session):
        return session.step(LiveInputs().advance())

    @staticmethod
    def names(events):
        return [row["name"] for row in events]

    def test_surface_refills_oxygen_and_clears_drowning_counter(self):
        session = self.make_session({"pos": [2, 0], "oxygen_ticks": 1, "zero_oxy_ticks": 12})

        events = self.step(session)

        self.assertEqual(events, [])
        self.assertEqual(session.sim.oxygen_ticks, 1 + self.tuning["gather"]["oxygen_refill_per_tick"])
        self.assertEqual(session.sim.zero_oxy_ticks, 0)

    def test_crossing_surface_boundary_emits_dive_and_surface(self):
        diving = self.make_session({"pos": [2, 0.49], "vel": [0, 4]})
        events = self.step(diving)
        self.assertEqual(self.names(events), ["dive"])
        self.assertLess(diving.sim.oxygen_ticks, diving.sim.oxygen_max)

        surfacing = self.make_session({"pos": [2, 0.51], "vel": [0, -4], "oxygen_ticks": 1})
        events = self.step(surfacing)
        self.assertEqual(self.names(events), ["surface"])
        self.assertGreater(surfacing.sim.oxygen_ticks, 1)

    def test_oxygen_empty_emits_once_when_oxygen_reaches_zero(self):
        session = self.make_session({"pos": [2, 5], "oxygen_ticks": 1})

        events = self.step(session)

        self.assertEqual(self.names(events), ["oxygen_empty"])
        self.assertEqual(session.sim.oxygen_ticks, 0)
        self.assertEqual(session.sim.zero_oxy_ticks, 1)

    def test_choke_deals_damage_at_configured_interval(self):
        interval = self.tuning["gather"]["choke_interval_ticks"]
        session = self.make_session({"pos": [2, 5], "oxygen_ticks": 0, "zero_oxy_ticks": interval - 1})

        events = self.step(session)

        self.assertEqual(self.names(events), ["choke"])
        self.assertEqual(session.sim.hp, self.tuning["gather"]["hp_max"] - 1)
        self.assertEqual(session.sim.zero_oxy_ticks, 0)
        self.assertFalse(session.done)

    def test_faint_clears_hold_and_finishes_with_empty_inventory(self):
        interval = self.tuning["gather"]["choke_interval_ticks"]
        session = self.make_session(
            {"pos": [2, 5], "oxygen_ticks": 0, "zero_oxy_ticks": interval - 1, "hp": 1},
            hold=["ca_loc", "bong_sung"],
        )

        events = self.step(session)

        self.assertEqual(self.names(events), ["choke", "faint", "gather_end"])
        self.assertTrue(session.done)
        self.assertEqual(session.end_row()["reason"], "fainted")
        self.assertEqual(session.sim.hold, [])
        self.assertEqual(events[-1]["data"]["inventory"], {"items": {}})
