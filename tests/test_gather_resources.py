"""Unit tests for Gather resource interactions owned by member 2."""

import json
import os
import tempfile
import unittest

from chonoi.contract import load_contract
from chonoi.inputs import LiveInputs
from chonoi.runner import Session


class GatherResources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tuning = load_contract()["tuning"]

    def session(self, player=None, hold=None, nodes=None, fish=None):
        block = {"player": player or {}}
        if hold is not None:
            block["hold"] = hold
        if nodes is not None:
            block["nodes"] = nodes
        if fish is not None:
            block["fish"] = fish
        return Session("gather", self.tuning, block, seed=1)

    @staticmethod
    def press(button):
        inputs = LiveInputs()
        inputs.set(**{button: True})
        return inputs.advance()

    @staticmethod
    def names(events):
        return [row["name"] for row in events]

    def test_interact_gathers_nearest_node_and_appends_to_lifo_hold(self):
        session = self.session(
            player={"pos": [10, 0]},
            nodes=[
                {"id": "N2", "kind": "bong_sung", "pos": [11, 0]},
                {"id": "N1", "kind": "bong_dien_dien", "pos": [11, 0]},
            ],
            fish=[],
        )

        events = session.step(self.press("interact"))

        self.assertEqual(self.names(events), ["gather"])
        self.assertEqual(events[0]["data"], {
            "node_id": "N1", "kind": "bong_dien_dien", "quantity": 1,
        })
        self.assertEqual(session.sim.hold, ["bong_dien_dien"])
        self.assertEqual(session.sim.nodes[1]["regrow_ticks"], int(self.tuning["gather"]["regrow_s"] * 60))

    def test_full_hold_emits_hold_full_without_consuming_node(self):
        capacity = self.tuning["gather"]["hold_capacity"]
        session = self.session(
            player={"pos": [10, 0]},
            hold=["ca_loc"] * capacity,
            nodes=[{"id": "N1", "kind": "bong_sung", "pos": [10, 0]}],
            fish=[],
        )

        events = session.step(self.press("interact"))

        self.assertEqual(self.names(events), ["hold_full"])
        self.assertEqual(session.sim.nodes[0]["regrow_ticks"], 0)
        self.assertEqual(len(session.sim.hold), capacity)

    def test_regrow_emits_event_when_node_becomes_ready(self):
        session = self.session(
            player={"pos": [10, 0]},
            nodes=[{"id": "N1", "kind": "bong_sung", "pos": [10, 0]}],
            fish=[],
        )
        session.step(self.press("interact"))
        session.sim.nodes[0]["regrow_ticks"] = 1

        events = session.step(LiveInputs().advance())

        self.assertEqual(self.names(events), ["node_regrown"])
        self.assertEqual(session.sim.nodes[0]["regrow_ticks"], 0)

    def test_interact_does_not_gather_underwater(self):
        session = self.session(
            player={"pos": [10, 1]},
            nodes=[{"id": "N1", "kind": "bong_sung", "pos": [10, 0]}],
            fish=[],
        )

        events = session.step(self.press("interact"))

        self.assertEqual(events, [])
        self.assertEqual(session.sim.hold, [])

    def test_catch_adds_fish_yield_removes_fish_and_starts_cooldown(self):
        session = self.session(
            player={"pos": [10, 5]},
            nodes=[],
            fish=[{"id": "F1", "kind": "ca_linh", "pos": [11, 5]}],
        )

        events = session.step(self.press("catch"))

        self.assertEqual(self.names(events), ["fish_caught"])
        self.assertEqual(events[0]["data"]["quantity"], self.tuning["gather"]["fish_yield"]["ca_linh"])
        self.assertEqual(session.sim.hold, ["ca_linh"] * 3)
        self.assertEqual(session.sim.fish, [])
        self.assertEqual(session.sim.catch_cd_ticks, int(self.tuning["gather"]["catch_cooldown_s"] * 60))

    def test_catch_requires_cooldown_and_does_not_duplicate_fish(self):
        session = self.session(
            player={"pos": [10, 5]},
            nodes=[],
            fish=[{"id": "F1", "kind": "ca_loc", "pos": [10, 5]}],
        )
        session.step(self.press("catch"))

        events = session.step(self.press("catch"))

        self.assertEqual(events, [])
        self.assertEqual(session.sim.hold, ["ca_loc"])

    def test_fish_hold_full_preserves_fish_and_cooldown(self):
        capacity = self.tuning["gather"]["hold_capacity"]
        session = self.session(
            player={"pos": [10, 5]},
            hold=["ca_loc"] * (capacity - 1),
            nodes=[],
            fish=[{"id": "F1", "kind": "ca_linh", "pos": [10, 5]}],
        )

        events = session.step(self.press("catch"))

        self.assertEqual(self.names(events), ["hold_full"])
        self.assertEqual(len(session.sim.fish), 1)
        self.assertEqual(session.sim.catch_cd_ticks, 0)

    def test_dock_interact_takes_priority_over_node_gather(self):
        session = self.session(
            player={"pos": [2, 0]},
            nodes=[{"id": "N1", "kind": "bong_sung", "pos": [2, 0]}],
            fish=[],
        )

        events = session.step(self.press("interact"))

        self.assertEqual(self.names(events), ["gather_end"])
        self.assertEqual(events[0]["data"]["reason"], "docked")
        self.assertEqual(session.sim.hold, [])

    def test_gather_end_contains_inventory_from_collected_resources(self):
        session = self.session(
            player={"pos": [10, 0]},
            nodes=[{"id": "N1", "kind": "bong_sung", "pos": [10, 0]}],
            fish=[],
        )
        gather_events = session.step(self.press("interact"))
        self.assertEqual(self.names(gather_events), ["gather"])

        session.sim.pos = [2.0, 0.0]
        end_events = session.step(self.press("interact"))

        self.assertEqual(self.names(end_events), ["gather_end"])
        self.assertEqual(end_events[0]["data"]["inventory"], {"items": {"bong_sung": 1}})
        self.assertEqual(session.end_row()["reason"], "docked")

    def test_inventory_out_is_written_once_after_gather_end(self):
        session = self.session(
            player={"pos": [10, 0]},
            nodes=[{"id": "N1", "kind": "bong_sung", "pos": [10, 0]}],
            fish=[],
        )
        session.step(self.press("interact"))

        with tempfile.TemporaryDirectory() as directory:
            path = f"{directory}/inventory.json"
            session.write_inventory_if_done(path)
            self.assertFalse(os.path.exists(path))

            session.sim.pos = [2.0, 0.0]
            session.step(self.press("interact"))
            session.write_inventory_if_done(path)

            with open(path, encoding="utf-8") as stream:
                self.assertEqual(json.load(stream), {"items": {"bong_sung": 1}})


if __name__ == "__main__":
    unittest.main()
