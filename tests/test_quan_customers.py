"""Quán lát 3: khách đến theo lịch, giữ chỗ nguyên liệu, kiên nhẫn, hết ca."""

import copy
import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.quan import QuanSim
from helpers import Workdir, events, read_jsonl, run_headless, write_json

DISH = "ca_loc_nuong_trui"
ALL_DISHES = {"ca_loc_nuong_trui", "goi_bong_sung", "lau_ca_linh_dien_dien"}
RICH = {"ca_loc": 5, "bong_sung": 5, "ca_linh": 5, "bong_dien_dien": 5}


def run(block, ticks, seed=1):
    with Workdir() as w:
        sc = write_json(w.path("sc.json"), {"quan": block})
        out = w.path("o.jsonl")
        code, err = run_headless("--mode", "quan", "--seed", str(seed), "--ticks", str(ticks),
                                 "--scenario", sc, "--out", out)
        assert code == 0, err
        with open(out, "rb") as f:
            raw = f.read()
        return read_jsonl(out), raw


def cust(**kw):
    c = {"id": "C1", "table_id": "T1", "dish_id": DISH}
    c.update(kw)
    return c


class Arrivals(unittest.TestCase):
    def test_khach_dau_den_tick_120(self):
        rows, _ = run({"stock": RICH}, 130)
        arr = events(rows, "customer_arrived")
        self.assertEqual([e["tick"] for e in arr], [120])
        d = arr[0]["data"]
        self.assertEqual((d["order_id"], d["table_id"]), ("C1", "T1"))
        self.assertIn(d["dish_id"], ALL_DISHES)
        snap = [r for r in rows if r["type"] == "snapshot" and r["tick"] == 120][0]
        c = snap["customers"][0]
        self.assertEqual(c["order_tick"], 120)
        self.assertEqual(c["order_status"], "reserved")
        self.assertEqual(c["patience_ticks_left"], 3600)

    def test_khach_ke_tiep_khi_ban_trong_lai(self):
        # chỉ ca_loc: khách 1 đến 120, hết kiên nhẫn 3720 (= 120 + 4 * 900) rồi lượt kế đến cùng tick
        rows, _ = run({"stock": {"ca_loc": 2}}, 3800)
        self.assertEqual([e["tick"] for e in events(rows, "customer_arrived")], [120, 3720])
        left = events(rows, "customer_left")
        self.assertEqual([e["tick"] for e in left], [3720])
        names = [r["name"] for r in rows if r["type"] == "event" and r["tick"] == 3720]
        self.assertEqual(names, ["customer_left", "customer_arrived"])

    def test_khong_du_mon_no_dish(self):
        rows, _ = run({"stock": {}}, 130)
        nd = events(rows, "no_dish")
        self.assertEqual([(e["tick"], e["data"]) for e in nd], [(120, {})])
        self.assertEqual(events(rows, "customer_arrived"), [])
        self.assertEqual([r for r in rows if r["type"] == "snapshot"][-1]["customers"], [])

    def test_ban_day_bo_luot(self):
        rows, _ = run({"stock": RICH}, 1100)
        self.assertEqual([e["tick"] for e in events(rows, "customer_arrived")], [120])
        self.assertEqual(events(rows, "no_dish"), [])  # lượt 1020 bị bỏ, không event

    def test_random_customers_false(self):
        rows, _ = run({"stock": RICH, "random_customers": False}, 200)
        self.assertEqual(events(rows, "customer_arrived"), [])
        self.assertEqual(events(rows, "no_dish"), [])

    def test_giu_cho_an_kho_voi_khach_sau(self):
        t = copy.deepcopy(load_contract()["tuning"])
        t["quan"]["tables"].append({"id": "T2", "pos": [12, 2]})
        sim = QuanSim(t, {"stock": {"ca_loc": 1}}, Streams(1), IdAllocator())
        inp = InputState((0.0, 0.0), {}, set())
        seen = []
        for _ in range(1020):
            seen += [(sim.phase_tick, n, d) for n, d in sim.step(inp)]
        self.assertEqual([s[:2] for s in seen], [(120, "customer_arrived"), (1020, "no_dish")])
        self.assertEqual(sim.customers[0]["reserved"], {"ca_loc": 1})
        self.assertEqual(sim._available()["ca_loc"], 0)
        self.assertEqual(sim.stock, {"ca_loc": 1})  # tồn vật lý không đổi
        # giữ chỗ là bản sao, không dùng chung với menu
        self.assertIsNot(sim.customers[0]["reserved"], sim.menu[DISH]["recipe"])

    def test_fixture_reserved_khong_dung_chung_menu(self):
        t = copy.deepcopy(load_contract()["tuning"])
        sim = QuanSim(t, {"stock": {"ca_loc": 1}, "customers": [cust()]}, Streams(1), IdAllocator())
        self.assertIsNot(sim.customers[0]["reserved"], sim.menu[DISH]["recipe"])


class Leaving(unittest.TestCase):
    def test_het_kien_nhan_tru_uy_tin(self):
        rows, _ = run({"stock": {"ca_loc": 1}, "random_customers": False,
                       "customers": [cust(patience_ticks_left=5)]}, 8)
        left = events(rows, "customer_left")
        self.assertEqual([(e["tick"], e["data"]) for e in left],
                         [(5, {"order_id": "C1", "table_id": "T1", "reason": "patience", "reputation": 2.5})])
        snaps = [r for r in rows if r["type"] == "snapshot"]
        self.assertEqual(snaps[0]["reputation"], 3.0)
        self.assertEqual(snaps[-1]["reputation"], 2.5)
        self.assertEqual(snaps[-1]["customers"], [])
        self.assertEqual(snaps[-1]["stock"], {"ca_loc": 1})  # nguyên liệu vẫn còn, giữ chỗ được nhả

    def test_het_ca_khach_cho_roi_closing(self):
        rows, _ = run({"stock": {"ca_loc": 1}, "random_customers": False, "time_left_ticks": 3,
                       "customers": [cust()]}, 10)
        left = events(rows, "customer_left")
        self.assertEqual([(e["tick"], e["data"]) for e in left],
                         [(3, {"order_id": "C1", "table_id": "T1", "reason": "closing", "reputation": 3.0})])
        qe = events(rows, "quan_end")
        self.assertEqual([e["tick"] for e in qe], [3])
        self.assertEqual(qe[0]["data"], {"reason": "time", "money": 0, "earned": 0,
                                         "shift_earned": 0, "reputation": 3.0})
        names = [r["name"] for r in rows if r["type"] == "event"]
        self.assertEqual(names, ["customer_left", "quan_end"])
        self.assertEqual(rows[-1]["type"], "end")
        self.assertEqual(rows[-1]["reason"], "time")
        self.assertEqual(rows[-1]["ticks"], 3)

    def test_het_ca_khong_sinh_khach(self):
        rows, _ = run({"stock": RICH, "time_left_ticks": 120}, 200)
        self.assertEqual(events(rows, "customer_arrived"), [])
        self.assertEqual([e["tick"] for e in events(rows, "quan_end")], [120])

    def test_roi_don_mon_tren_bep_va_tay(self):
        t = copy.deepcopy(load_contract()["tuning"])
        pl = {"order_id": "C1", "dish_id": DISH, "base_price": 60}
        sc = {"stock": {"ca_loc": 1}, "random_customers": False,
              "customers": [cust(order_status="assigned", reserved={}, patience_ticks_left=1)],
              "stoves": [{"id": "B1", "state": "cooking", "dish": pl, "cook_ticks_left": 50}]}
        sim = QuanSim(t, sc, Streams(1), IdAllocator())
        sim.step(InputState((0.0, 0.0), {}, set()))
        s = sim.stoves[0]
        self.assertEqual((s["state"], s["dish"], s["cook_ticks_left"], s["ready_ticks"]), ("idle", None, 0, 0))
        sc = {"stock": {"ca_loc": 1}, "random_customers": False, "hand": pl,
              "customers": [cust(order_status="assigned", reserved={}, patience_ticks_left=1)]}
        sim = QuanSim(t, sc, Streams(1), IdAllocator())
        sim.step(InputState((0.0, 0.0), {}, set()))
        self.assertIsNone(sim.hand)


class Determinism(unittest.TestCase):
    def test_cung_seed_giong_byte(self):
        a = run({"stock": RICH}, 2500, seed=7)[1]
        b = run({"stock": RICH}, 2500, seed=7)[1]
        self.assertEqual(a, b)

    def test_seed_khac_van_chon_mon_hop_le(self):
        for seed in range(1, 8):
            rows, _ = run({"stock": {"ca_loc": 1, "bong_sung": 2}}, 130, seed=seed)
            d = events(rows, "customer_arrived")[0]["data"]["dish_id"]
            self.assertIn(d, {"ca_loc_nuong_trui", "goi_bong_sung"})


if __name__ == "__main__":
    unittest.main()
