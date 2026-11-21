"""Quán v1.1: 4 bàn, 2 bếp, món mới, lọc món theo kế hoạch ngày (plan_dishes)."""

import copy
import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.quan import QuanSim
from helpers import Workdir, events, read_jsonl, run_headless, write_json

BIG = {k: 20 for k in ("ca_loc", "bong_sung", "ca_linh", "bong_dien_dien", "ca_keo", "keo_neo")}
IDLE = InputState((0.0, 0.0), {}, set())
PRESS = InputState((0.0, 0.0), {}, {"interact"})


def run(block, ticks, seed=1):
    with Workdir() as w:
        sc = write_json(w.path("sc.json"), {"quan": block})
        out = w.path("o.jsonl")
        code, err = run_headless("--mode", "quan", "--seed", str(seed), "--ticks", str(ticks),
                                 "--scenario", sc, "--out", out)
        assert code == 0, err
        return read_jsonl(out)


def make(scenario, seed=1, plan=None):
    t = copy.deepcopy(load_contract()["tuning"])
    return QuanSim(t, scenario, Streams(seed), IdAllocator(), plan_dishes=plan)


def cust(cid="C1", table="T1", dish="ca_loc_nuong_trui", **kw):
    c = {"id": cid, "table_id": table, "dish_id": dish}
    c.update(kw)
    return c


def collect(sim, ticks):
    out = []
    for _ in range(ticks):
        for n, d in sim.step(IDLE):
            out.append((sim.phase_tick, n, d))
    return out


class Tables(unittest.TestCase):
    def test_bon_khach_ngoi_t1_den_t4(self):
        rows = run({"stock": BIG}, 2900)
        arr = events(rows, "customer_arrived")
        self.assertEqual([e["tick"] for e in arr], [120, 1020, 1920, 2820])
        self.assertEqual([e["data"]["table_id"] for e in arr], ["T1", "T2", "T3", "T4"])
        self.assertEqual([e["data"]["order_id"] for e in arr], ["C1", "C2", "C3", "C4"])

    def test_khach_thu_5_tick_3720_ngoi_lai_t1_sau_khi_t1_roi(self):
        # T1 vào 120, kiên nhẫn 3600 -> rời ở 3720 (bước 4) rồi lượt sinh 3720 (bước 5) thấy T1 trống
        rows = run({"stock": BIG}, 3730)
        arr = events(rows, "customer_arrived")
        self.assertEqual([e["tick"] for e in arr], [120, 1020, 1920, 2820, 3720])
        self.assertEqual(arr[4]["data"]["table_id"], "T1")
        self.assertEqual(arr[4]["data"]["order_id"], "C5")
        left = events(rows, "customer_left")
        self.assertEqual([(e["tick"], e["data"]["table_id"], e["data"]["reason"]) for e in left],
                         [(3720, "T1", "patience")])
        self.assertEqual(events(rows, "no_dish"), [])
        self.assertEqual([r["name"] for r in rows if r["type"] == "event" and r["tick"] == 3720],
                         ["customer_left", "customer_arrived"])

    def test_bon_ban_kin_luot_sinh_bi_bo_khong_event(self):
        full = [cust(f"C{i}", f"T{i}") for i in range(1, 5)]
        rows = run({"stock": BIG, "customers": full}, 3599)
        self.assertEqual(events(rows, "customer_arrived"), [])
        self.assertEqual(events(rows, "no_dish"), [])
        self.assertEqual(events(rows, "customer_left"), [])


class Stoves(unittest.TestCase):
    def test_hai_bep_nau_song_song(self):
        sim = make({"stock": BIG, "random_customers": False, "player": {"pos": [3.5, 8.0]},
                    "customers": [cust("C1", "T1", "ca_loc_nuong_trui"),
                                  cust("C2", "T2", "goi_bong_sung")]})
        sim.step(PRESS)  # hòa khoảng cách -> B1, đơn cũ nhất (hòa order_tick) theo bàn T1
        sim.pos = [3.6, 8.0]
        sim.step(PRESS)  # chỉ B2 trong tầm
        b1, b2 = sim.stoves
        self.assertEqual((b1["state"], b1["dish"]["order_id"], b1["cook_ticks_left"]), ("cooking", "C1", 359))
        self.assertEqual((b2["state"], b2["dish"]["order_id"], b2["cook_ticks_left"]), ("cooking", "C2", 240))
        evs = collect(sim, 240)
        self.assertEqual([(t, n, d["stove_id"]) for t, n, d in evs], [(242, "dish_ready", "B2")])
        self.assertEqual((sim.stoves[0]["state"], sim.stoves[0]["cook_ticks_left"]), ("cooking", 119))

    def test_interact_chon_bep_gan_hon_hoa_thi_id(self):
        for pos, want in (([3.4, 8.0], "B1"), ([3.6, 8.0], "B2"), ([3.5, 8.0], "B1")):
            sim = make({"stock": BIG, "random_customers": False, "player": {"pos": pos},
                        "customers": [cust()]})
            evs = sim.step(PRESS)
            self.assertEqual([(n, d["stove_id"]) for n, d in evs], [("cook_started", want)], pos)

    def test_bep_idle_lay_don_reserved_cu_nhat(self):
        sim = make({"stock": BIG, "random_customers": False, "player": {"pos": [2.0, 8.0]},
                    "customers": [cust("C1", "T1", order_tick=500),
                                  cust("C2", "T3", "goi_bong_sung", order_tick=100),
                                  cust("C3", "T2", "goi_bong_sung", order_tick=100)]})
        evs = sim.step(PRESS)
        self.assertEqual(evs[0][1]["order_id"], "C3")  # order_tick nhỏ nhất, hòa -> bàn T2 trước T3


class PlanFilter(unittest.TestCase):
    def test_ke_hoach_chi_ca_keo_kho_chi_du_goi_thi_no_dish(self):
        sim = make({"stock": {"bong_sung": 2}}, plan={"ca_keo_nuong"})
        self.assertEqual(collect(sim, 120), [(120, "no_dish", {})])
        self.assertEqual(sim.customers, [])

    def test_ke_hoach_chon_chi_mon_trong_ke_hoach_qua_nhieu_seed(self):
        plan = {"ca_keo_nuong", "goi_bong_sung"}
        for seed in range(1, 11):
            sim = make({"stock": BIG}, seed=seed, plan=plan)
            arr = [d for _, n, d in collect(sim, 2900) if n == "customer_arrived"]
            self.assertEqual(len(arr), 4)
            for d in arr:
                self.assertIn(d["dish_id"], plan, seed)

    def test_ke_hoach_loc_truoc_roi_moi_loc_kho(self):
        # kho chỉ đủ gỏi + cá kéo; kế hoạch có gỏi và lẩu mắm (thiếu kho) -> luôn gỏi
        for seed in range(1, 6):
            sim = make({"stock": {"bong_sung": 2, "ca_keo": 2}}, seed=seed, plan={"goi_bong_sung", "lau_mam"})
            self.assertEqual([d["dish_id"] for _, n, d in collect(sim, 130)], ["goi_bong_sung"])

    def test_khong_ke_hoach_dung_ca_6_mon(self):
        seen = set()
        for seed in range(1, 31):
            sim = make({"stock": BIG}, seed=seed)
            seen |= {d["dish_id"] for _, n, d in collect(sim, 2900) if n == "customer_arrived"}
        self.assertIn("ca_keo_nuong", seen)
        self.assertIn("lau_mam", seen)

    def test_fixture_khach_ngoai_ke_hoach_bad_input(self):
        with self.assertRaises(BadInput):
            make({"stock": BIG, "customers": [cust()]}, plan={"goi_bong_sung"})
        make({"stock": BIG, "customers": [cust(dish="goi_bong_sung")]}, plan={"goi_bong_sung"})


class NewDish(unittest.TestCase):
    def test_lau_mam_720_tick_gia_200_boa_40(self):
        stock = {"bong_dien_dien": 1, "ca_keo": 1, "ca_linh": 2, "keo_neo": 1}
        sim = make({"stock": stock, "random_customers": False, "player": {"pos": [2.0, 8.0]},
                    "customers": [cust(dish="lau_mam")]})
        evs = sim.step(PRESS)
        self.assertEqual(evs[0][0], "cook_started")
        self.assertEqual(evs[0][1]["base_price"], 200)
        self.assertEqual(sim.stoves[0]["cook_ticks_left"], 720)
        self.assertEqual(sim.stock, {})
        ready = [t for t, n, _ in collect(sim, 720) if n == "dish_ready"]
        self.assertEqual(ready, [721])
        sim.step(PRESS)  # lấy món
        sim.pos = [9.0, 2.0]
        evs = sim.step(PRESS)
        self.assertEqual([(n, d["base_price"], d["tip"]) for n, d in evs], [("served", 200, 40)])


if __name__ == "__main__":
    unittest.main()
