"""Adapter kho cá thể v1.2 (Ticket-03): đọc/ghi, contract và scenario, chạy trong tiến trình."""

import copy
import json
import unittest
from fractions import Fraction

from chonoi import fresh
from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.inventory import read_inventory, validate_item_list, write_inventory
from chonoi.scenario import load_scenario
from helpers import ROOT, Workdir, write_json

FRESHNESS = {"initial": 100, "gather_decay_per_s": 0.5, "quan_decay_per_s": 0.25, "spoiled_below": 30}


def base_contract():
    with open(ROOT + "/game.contract.json", encoding="utf-8") as f:
        return json.load(f)


def v12_tuning():
    t = copy.deepcopy(base_contract()["tuning"])
    t["freshness"] = dict(FRESHNESS)
    return t


def item(i, kind="ca_loc", f=100):
    return {"id": i, "kind": kind, "fresh": f}


class InventoryV12(unittest.TestCase):
    def roundtrip(self, items):
        with Workdir() as w:
            p = w.path("inv.json")
            write_inventory(p, validate_item_list(items))
            return read_inventory(p)

    def test_roundtrip_exact_values(self):
        vals = [97.5, 7199 / 240, 30, 0, 100]
        items = [item(f"I{n}", "ca_loc", v) for n, v in enumerate(vals, 1)]
        back = self.roundtrip(items)
        self.assertEqual([e["id"] for e in back], [f"I{n}" for n in range(1, 6)])
        self.assertEqual([e["fresh"] for e in back],
                         [Fraction(195, 2), Fraction(7199, 240), 30, 0, 100])
        self.assertTrue(all(e["kind"] == "ca_loc" for e in back))

    def test_threshold_branch_survives_roundtrip(self):
        th = fresh.threshold(v12_tuning())
        just_below = Fraction(7199, 240)
        back = self.roundtrip([item("I1", "ca_linh", float(just_below)), item("I2", "ca_linh", 30)])
        self.assertTrue(back[0]["fresh"] < th)
        self.assertFalse(back[1]["fresh"] < th)

    def test_write_sorted_by_id(self):
        with Workdir() as w:
            p = w.path("inv.json")
            write_inventory(p, validate_item_list([item("I10"), item("I2"), item("I1")]))
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        self.assertEqual([e["id"] for e in data["items"]], ["I1", "I2", "I10"])
        self.assertEqual(set(data), {"items"})

    def test_write_empty_list(self):
        self.assertEqual(self.roundtrip([]), [])

    def test_rejects_bad_items(self):
        bad = [
            [item("I1", "ca_la")],
            [item("I1"), item("I1", "ca_linh")],
            [item("")],
            [item("I1", "ca_loc", 100.5)],
            [item("I1", "ca_loc", -1)],
            [item("I1", "ca_loc", "50")],
            [item("I1", "ca_loc", True)],
            [item("I1", "ca_loc", float("nan"))],
            [{"id": "I1", "kind": "ca_loc"}],
            [{"id": "I1", "kind": "ca_loc", "fresh": 5, "x": 1}],
            ["I1"],
        ]
        for items in bad:
            with self.subTest(items=items), self.assertRaises(BadInput):
                validate_item_list(items)

    def test_read_rejects_bad_files(self):
        cases = [
            {"items": [], "extra": 1},
            {"items": "x"},
            {"items": 3},
            {"items": [item("I1", "zzz")]},
            {"foo": []},
        ]
        with Workdir() as w:
            for i, data in enumerate(cases):
                p = write_json(w.path(f"b{i}.json"), data)
                with self.subTest(data=data), self.assertRaises(BadInput):
                    read_inventory(p)

    def test_read_nan_literal_file(self):
        with Workdir() as w:
            p = w.path("nan.json")
            with open(p, "w", encoding="utf-8") as f:
                f.write('{"items":[{"id":"I1","kind":"ca_loc","fresh":NaN}]}')
            with self.assertRaises(BadInput):
                read_inventory(p)

    def test_read_count_schema_still_works(self):
        with Workdir() as w:
            p = write_json(w.path("c.json"), {"items": {"ca_loc": 2, "ca_linh": 0}})
            self.assertEqual(read_inventory(p), {"ca_loc": 2})
            q = w.path("o.json")
            write_inventory(q, {"ca_loc": 2, "ca_linh": 0})
            self.assertEqual(read_inventory(q), {"ca_loc": 2})

    def test_fresh_helpers(self):
        t = v12_tuning()
        self.assertTrue(fresh.enabled(t))
        self.assertFalse(fresh.enabled(base_contract()["tuning"]))
        self.assertEqual(fresh.per_tick(t, "gather"), Fraction(1, 120))
        self.assertEqual(fresh.per_tick(t, "quan"), Fraction(1, 240))
        self.assertEqual(fresh.threshold(t), 30)
        self.assertEqual(fresh.to_json(Fraction(195, 2)), 97.5)
        self.assertEqual(fresh.parse(7199 / 240), Fraction(7199, 240))


class ContractV12(unittest.TestCase):
    def load(self, mutate):
        c = base_contract()
        mutate(c)
        with Workdir() as w:
            return load_contract(write_json(w.path("c.json"), c))

    def test_repo_contract_still_loads(self):
        self.assertNotIn("freshness", load_contract()["tuning"])

    def test_valid_v12(self):
        def m(c):
            c["contract_version"] = "1.2"
            c["tuning"]["freshness"] = dict(FRESHNESS)
        self.assertEqual(self.load(m)["contract_version"], "1.2")

    def test_rejects_v12_without_freshness(self):
        with self.assertRaises(BadInput):
            self.load(lambda c: c.update(contract_version="1.2"))

    def test_rejects_freshness_with_old_version(self):
        with self.assertRaises(BadInput):
            self.load(lambda c: c["tuning"].update(freshness=dict(FRESHNESS)))

    def test_rejects_bad_freshness_block(self):
        for patch in ({"initial": 90}, {"gather_decay_per_s": 0}, {"quan_decay_per_s": -1},
                      {"spoiled_below": 100}, {"spoiled_below": 0}, {"extra": 1}):
            def m(c, patch=patch):
                c["contract_version"] = "1.2"
                c["tuning"]["freshness"] = {**FRESHNESS, **patch}
            with self.subTest(patch=patch), self.assertRaises(BadInput):
                self.load(m)


class ScenarioV12(unittest.TestCase):
    def scenario(self, mode, block, tuning=None):
        with Workdir() as w:
            p = write_json(w.path("s.json"), {mode: block})
            return load_scenario(p, mode, tuning or v12_tuning())

    def test_stock_dict_rejected(self):
        with self.assertRaises(BadInput):
            self.scenario("quan", {"stock": {"ca_loc": 2}})

    def test_stock_array_ok(self):
        b = self.scenario("quan", {"stock": [item("I1"), item("I2", "ca_linh", 97.5)]})
        self.assertEqual(len(b["stock"]), 2)

    def test_hold_array_ok_and_capacity(self):
        self.scenario("gather", {"hold": [item("I1", "ca_linh")]})
        cap = v12_tuning()["gather"]["hold_capacity"]
        with self.assertRaises(BadInput):
            self.scenario("gather", {"hold": [item(f"I{n}") for n in range(cap + 1)]})

    def test_hold_kind_strings_rejected(self):
        with self.assertRaises(BadInput):
            self.scenario("gather", {"hold": ["ca_loc"]})

    def test_reserved_array_of_ids(self):
        t = v12_tuning()
        dish = sorted(t["menu"])[0]
        tid = t["quan"]["tables"][0]["id"]
        cust = {"id": "C1", "table_id": tid, "dish_id": dish}
        self.scenario("quan", {"customers": [{**cust, "reserved": ["I1", "I2"]}]})
        for bad in ({"ca_loc": 1}, ["I1", "I1"], [""], [1]):
            with self.subTest(bad=bad), self.assertRaises(BadInput):
                self.scenario("quan", {"customers": [{**cust, "reserved": bad}]})

    def test_flag_off_keeps_count_schema(self):
        t = base_contract()["tuning"]
        self.scenario("quan", {"stock": {"ca_loc": 2}}, t)
        self.scenario("gather", {"hold": ["ca_loc"]}, t)
        with self.assertRaises(BadInput):
            self.scenario("quan", {"stock": [item("I1")]}, t)


if __name__ == "__main__":
    unittest.main()
