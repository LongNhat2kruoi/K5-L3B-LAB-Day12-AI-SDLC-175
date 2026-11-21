"""Quán v1.2 (Ticket-03): độ tươi, hao kho, ươn, giữ theo id, giá theo tươi. Chạy trong tiến trình."""

import unittest
from fractions import Fraction

from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.runner import run
from chonoi.sim.quan import QuanSim
from helpers import Workdir, events, read_jsonl, snapshots
from test_inventory_v12 import flag_off_tuning, item, v12_tuning

IDLE = InputState((0.0, 0.0), {}, set())
PRESS = InputState((0.0, 0.0), {}, {"interact"})
LOC = "ca_loc_nuong_trui"          # 1 ca_loc, giá 60
LAU = "lau_ca_linh_dien_dien"      # 3 ca_linh + 1 bong_dien_dien, giá 120
B1 = [2, 8]


def make(stock, customers=(), tuning=None, **extra):
    sc = {"stock": stock, "customers": list(customers), "random_customers": False, **extra}
    return QuanSim(tuning or v12_tuning(), sc, Streams(1), IdAllocator())


def cust(cid="C1", table="T1", dish=LOC, **kw):
    return {"id": cid, "table_id": table, "dish_id": dish, **kw}


def collect(sim, ticks, inp=IDLE):
    out = []
    for _ in range(ticks):
        for n, d in sim.step(inp):
            out.append((sim.phase_tick, n, d))
    return out


def spoiled(evs):
    return [(t, d["item_id"]) for t, n, d in evs if n == "spoiled"]


def fresh_of(sim, i):
    return next(it["fresh"] for it in sim.items if it["id"] == i)


class Decay(unittest.TestCase):
    def test_fresh_30_spoils_at_tick_1_exactly_once(self):
        sim = make([item("I1", "ca_loc", 30)])
        self.assertEqual(spoiled(collect(sim, 10)), [(1, "I1")])

    def test_just_above_threshold_spoils_at_tick_2(self):
        sim = make([item("I1", "ca_loc", 7201 / 240)])
        self.assertEqual(fresh_of(sim, "I1"), Fraction(7201, 240))
        self.assertEqual(spoiled(collect(sim, 5)), [(2, "I1")])

    def test_already_spoiled_never_emits(self):
        sim = make([item("I1", "ca_loc", 10)])
        self.assertEqual(spoiled(collect(sim, 5)), [])

    def test_multiple_spoil_in_id_order(self):
        sim = make([item("I10", "ca_loc", 30), item("I2", "ca_linh", 30), item("I1", "keo_neo", 90)])
        evs = collect(sim, 1)
        self.assertEqual(spoiled(evs), [(1, "I2"), (1, "I10")])
        self.assertEqual(evs[0][2], {"item_id": "I2", "kind": "ca_linh", "location": "stock"})

    def test_decay_quarter_per_second_exact(self):
        sim = make([item("I1", "ca_loc", 100)])
        collect(sim, 240)
        self.assertEqual(fresh_of(sim, "I1"), Fraction(99))

    def test_decay_clamped_at_zero(self):
        sim = make([item("I1", "ca_loc", 0.5)])
        collect(sim, 200)
        self.assertEqual(fresh_of(sim, "I1"), 0)

    def test_held_items_decay_too(self):
        sim = make([item("I1", "ca_loc", 100)], [cust()])
        collect(sim, 240)
        self.assertEqual(fresh_of(sim, "I1"), Fraction(99))


class Reservation(unittest.TestCase):
    def test_new_customer_holds_freshest_then_smallest_id(self):
        sim = make([item("I1", "ca_loc", 80), item("I2", "ca_loc", 95), item("I3", "ca_loc", 95)])
        sim.random_customers = True
        sim.phase_tick = sim.t["first_customer_tick"] - 1
        collect(sim, 1)
        self.assertEqual(sim.customers[0]["reserved"], ["I2"])

    def test_fixture_missing_reserved_allocated_by_order_tick_then_table(self):
        stock = [item("I1", "ca_loc", 90), item("I2", "ca_loc", 100), item("I3", "ca_loc", 95)]
        sim = make(stock, [cust("C1", "T1", order_tick=5), cust("C2", "T2", order_tick=1),
                           cust("C3", "T3", order_tick=5)])
        got = {c["id"]: c["reserved"] for c in sim.customers}
        self.assertEqual(got, {"C2": ["I2"], "C1": ["I3"], "C3": ["I1"]})

    def test_held_item_spoils_then_rereserved_with_other(self):
        sim = make([item("I1", "ca_loc", 30), item("I2", "ca_loc", 90)], [cust(reserved=["I1"])])
        evs = collect(sim, 1)
        self.assertEqual(spoiled(evs), [(1, "I1")])
        self.assertEqual(sim.customers[0]["reserved"], ["I2"])
        self.assertEqual(sim.customers[0]["order_status"], "reserved")

    def test_not_enough_becomes_unfulfillable_then_patience_leave(self):
        sim = make([item("I1", "ca_loc", 30)], [cust(reserved=["I1"], patience_ticks_left=3)])
        evs = collect(sim, 5)
        self.assertEqual(sim.customers, [])
        left = [(t, d["reason"]) for t, n, d in evs if n == "customer_left"]
        self.assertEqual(left, [(3, "patience")])
        self.assertEqual(spoiled(evs), [(1, "I1")])

    def test_unfulfillable_state_snapshot(self):
        sim = make([item("I1", "ca_loc", 30)], [cust(reserved=["I1"], patience_ticks_left=50)])
        collect(sim, 1)
        c = sim.snapshot()["customers"][0]
        self.assertEqual((c["order_status"], c["reserved"], c["state"]), ("unfulfillable", [], "waiting"))

    def test_rereserve_in_order_tick_then_table_order(self):
        # C1 (order_tick 2) giữ I1; C2 (order_tick 1) giữ I2; cả hai ươn; I3 chỉ đủ cho đơn xử lý trước (C2)
        stock = [item("I1", "ca_loc", 30), item("I2", "ca_loc", 30), item("I3", "ca_loc", 90)]
        sim = make(stock, [cust("C1", "T1", order_tick=2, reserved=["I1"]),
                           cust("C2", "T2", order_tick=1, reserved=["I2"])])
        collect(sim, 1)
        st = {c["id"]: (c["order_status"], c["reserved"]) for c in sim.customers}
        self.assertEqual(st, {"C2": ("reserved", ["I3"]), "C1": ("unfulfillable", [])})

    def test_new_customer_skips_spoiled_and_held(self):
        sim = make([item("I1", "ca_loc", 10), item("I2", "ca_loc", 90)], [cust()])
        self.assertEqual(sim._available()["ca_loc"], 0)  # I1 ươn, I2 đã giữ
        sim.random_customers = True
        sim.phase_tick = sim.t["first_customer_tick"] - 1
        evs = collect(sim, 1)
        self.assertIn("no_dish", [n for _, n, _ in evs])


class Pricing(unittest.TestCase):
    def cook(self, sim):
        sim.pos = list(B1)
        return collect(sim, 1, PRESS)

    def test_lau_price_by_mean_fresh_and_tip(self):
        # sau 1 tick hao (-1/240 mỗi cá thể): tổng còn 350 -> mean 87.5 -> floor(120 * 87.5 / 100) = 105
        stock = [item("I1", "ca_linh", 100), item("I2", "ca_linh", 100), item("I3", "ca_linh", 100),
                 item("I4", "bong_dien_dien", 50 + 4 / 240)]
        sim = make(stock, [cust(dish=LAU)])
        evs = self.cook(sim)
        cs = [d for _, n, d in evs if n == "cook_started"][0]
        self.assertEqual(cs["base_price"], 105)
        self.assertEqual(sim.stoves[0]["dish"]["base_price"], 105)
        self.assertEqual(sim.stock, [])  # tiêu đúng các id đang giữ
        collect(sim, 600)
        collect(sim, 1, PRESS)  # lấy món
        self.assertIsNotNone(sim.hand)
        sim.pos = list(sim.tables[0]["pos"])
        served = [d for _, n, d in collect(sim, 1, PRESS) if n == "served"][0]
        self.assertEqual((served["base_price"], served["tip"]), (105, 21))

    def test_cook_started_items_sorted_by_kind_then_id(self):
        stock = [item("I10", "ca_linh", 100), item("I2", "ca_linh", 100), item("I3", "ca_linh", 100),
                 item("I1", "bong_dien_dien", 100), item("I9", "ca_loc", 100)]
        sim = make(stock, [cust(dish=LAU)])
        cs = [d for _, n, d in self.cook(sim) if n == "cook_started"][0]
        self.assertEqual([(i["kind"], i["id"]) for i in cs["items"]],
                         [("bong_dien_dien", "I1"), ("ca_linh", "I2"), ("ca_linh", "I3"), ("ca_linh", "I10")])
        self.assertTrue(all(isinstance(i["fresh"], float) for i in cs["items"]))
        self.assertEqual([i["id"] for i in sim.stock], ["I9"])

    def test_full_fresh_after_decay_floors(self):
        sim = make([item("I1", "ca_loc", 100)], [cust()])
        cs = [d for _, n, d in self.cook(sim) if n == "cook_started"][0]
        self.assertEqual(cs["base_price"], 59)  # floor(60 * (100 - 1/240) / 100)


class Schema(unittest.TestCase):
    def test_snapshot_schema(self):
        sim = make([item("I10", "ca_loc", 20), item("I2", "ca_linh", 97.5), item("I1", "ca_loc", 100)],
                   [cust(reserved=["I1"])])
        snap = sim.snapshot()
        self.assertEqual([(i["id"], i["kind"]) for i in snap["stock"]],
                         [("I1", "ca_loc"), ("I2", "ca_linh"), ("I10", "ca_loc")])
        self.assertEqual(snap["stock"][1]["fresh"], 97.5)
        self.assertEqual(snap["customers"][0]["reserved"], ["I1"])
        self.assertNotIn("held", snap["customers"][0])

    def test_inventory_file_param_accepts_list(self):
        sc = {"customers": [], "random_customers": False}
        sim = QuanSim(v12_tuning(), sc, Streams(1), IdAllocator(),
                      inventory=[{"id": "I1", "kind": "ca_loc", "fresh": Fraction(50)}])
        self.assertEqual(sim.snapshot()["stock"], [{"id": "I1", "kind": "ca_loc", "fresh": 50.0}])

    def test_count_stock_rejected_in_v12(self):
        with self.assertRaises(BadInput):
            make({"ca_loc": 2})
        with self.assertRaises(BadInput):
            QuanSim(v12_tuning(), {}, Streams(1), IdAllocator(), inventory={"ca_loc": 2})

    def test_item_stock_rejected_in_v11(self):
        t = flag_off_tuning()
        with self.assertRaises(BadInput):
            QuanSim(t, {"stock": [item("I1")]}, Streams(1), IdAllocator())
        with self.assertRaises(BadInput):
            QuanSim(t, {}, Streams(1), IdAllocator(), inventory=[{"id": "I1", "kind": "ca_loc", "fresh": Fraction(1)}])

    def test_reserved_map_rejected_in_v12_and_list_in_v11(self):
        with self.assertRaises(BadInput):
            make([item("I1")], [cust(reserved={"ca_loc": 1})])
        with self.assertRaises(BadInput):
            QuanSim(flag_off_tuning(), {"stock": {"ca_loc": 1}, "customers": [cust(reserved=["I1"])]},
                    Streams(1), IdAllocator())


class FixtureChecks(unittest.TestCase):
    def bad(self, stock, customers):
        with self.assertRaises(BadInput):
            make(stock, customers)

    def test_reserved_unknown_id(self):
        self.bad([item("I1")], [cust(reserved=["I9"])])

    def test_reserved_spoiled_item(self):
        self.bad([item("I1", "ca_loc", 29)], [cust(reserved=["I1"])])

    def test_reserved_shared_between_orders(self):
        self.bad([item("I1")], [cust("C1", "T1", reserved=["I1"]), cust("C2", "T2", reserved=["I1"])])

    def test_reserved_wrong_recipe(self):
        self.bad([item("I1", "ca_linh")], [cust(reserved=["I1"])])
        self.bad([item("I1"), item("I2")], [cust(reserved=["I1", "I2"])])

    def test_missing_reserved_not_enough_stock(self):
        self.bad([item("I1")], [cust("C1", "T1"), cust("C2", "T2")])
        self.bad([item("I1", "ca_loc", 10)], [cust()])

    def test_missing_reserved_skips_items_held_explicitly(self):
        sim = make([item("I1", "ca_loc", 100), item("I2", "ca_loc", 60)],
                   [cust("C1", "T1", order_tick=0), cust("C2", "T2", order_tick=9, reserved=["I1"])])
        got = {c["id"]: c["reserved"] for c in sim.customers}
        self.assertEqual(got, {"C1": ["I2"], "C2": ["I1"]})


class Determinism(unittest.TestCase):
    def test_same_bytes_twice(self):
        stock = [item(f"I{n}", k, 100 - n) for n, k in enumerate(
            ["ca_loc", "ca_loc", "bong_sung", "bong_sung", "ca_linh", "ca_linh", "ca_linh", "bong_dien_dien"], 1)]
        stock[7] = item("I8", "bong_dien_dien", 30)
        sc = {"stock": stock, "player": {"pos": B1}}
        frames = [{"tick": 0, "interact": True}, {"tick": 1, "interact": False}, {"tick": 200, "interact": True}]
        outs = []
        for _ in range(2):
            with Workdir() as w:
                p = w.path("o.jsonl")
                run("quan", v12_tuning(), sc, 7, frames, 900, p, 10)
                with open(p, "rb") as f:
                    outs.append(f.read())
        self.assertEqual(outs[0], outs[1])
        self.assertIn(b'"name":"spoiled"', outs[0])

    def test_runner_spoiled_event_tick_and_snapshot(self):
        sc = {"stock": [item("I1", "ca_loc", 30)], "random_customers": False}
        with Workdir() as w:
            p = w.path("o.jsonl")
            run("quan", v12_tuning(), sc, 1, [], 3, p, 1)
            rows = read_jsonl(p)
        ev = events(rows, "spoiled")
        self.assertEqual([(e["tick"], e["data"]) for e in ev],
                         [(1, {"item_id": "I1", "kind": "ca_loc", "location": "stock"})])
        snaps = snapshots(rows)
        self.assertEqual(snaps[0]["stock"], [{"id": "I1", "kind": "ca_loc", "fresh": 30.0}])
        self.assertAlmostEqual(snaps[2]["stock"][0]["fresh"], 30 - 2 / 240, delta=0.001)


if __name__ == "__main__":
    unittest.main()
