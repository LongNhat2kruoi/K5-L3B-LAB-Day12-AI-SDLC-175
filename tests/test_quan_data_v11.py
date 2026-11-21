"""Quán v1.1 (TICKET-02): 2 bếp / 4 bàn, 6 món, day_plan, nguyên liệu ca_keo / keo_neo."""

import json
import os
import unittest

from helpers import ROOT, Workdir, read_jsonl, run_headless, snapshots, write_json

with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as _f:
    TUNING = json.load(_f)["tuning"]

MENU = {
    "ca_loc_nuong_trui": ({"ca_loc": 1}, 6, 60),
    "goi_bong_sung": ({"bong_sung": 2}, 4, 40),
    "lau_ca_linh_dien_dien": ({"ca_linh": 3, "bong_dien_dien": 1}, 10, 120),
    "canh_chua_ca_loc": ({"ca_loc": 1, "bong_dien_dien": 1}, 8, 90),
    "ca_keo_nuong": ({"ca_keo": 2}, 6, 70),
    "lau_mam": ({"ca_linh": 2, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 1}, 12, 200),
}

# Bảng D1-D5 nguyên văn từ spec: (món x suất, nguyên liệu cần)
PLAN = {
    1: ({"ca_loc_nuong_trui": 3, "goi_bong_sung": 3}, {"ca_loc": 3, "bong_sung": 6}),
    2: ({"ca_loc_nuong_trui": 2, "lau_ca_linh_dien_dien": 2},
        {"ca_loc": 2, "ca_linh": 6, "bong_dien_dien": 2}),
    3: ({"goi_bong_sung": 2, "canh_chua_ca_loc": 2, "ca_keo_nuong": 2},
        {"bong_sung": 4, "ca_loc": 2, "bong_dien_dien": 2, "ca_keo": 4}),
    4: ({"lau_mam": 1, "ca_loc_nuong_trui": 2, "goi_bong_sung": 1},
        {"ca_linh": 2, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 1, "ca_loc": 2, "bong_sung": 2}),
    5: ({"lau_mam": 1, "lau_ca_linh_dien_dien": 1, "ca_loc_nuong_trui": 1},
        {"ca_linh": 5, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 2, "ca_loc": 1}),
}


class Layout(unittest.TestCase):
    def test_bep_va_ban(self):
        q = TUNING["quan"]
        self.assertEqual([(s["id"], s["pos"]) for s in q["stoves"]], [("B1", [2, 8]), ("B2", [5, 8])])
        self.assertEqual([(t["id"], t["pos"]) for t in q["tables"]],
                         [("T1", [9, 2]), ("T2", [13, 2]), ("T3", [9, 6]), ("T4", [13, 6])])

    def test_snapshot_tick0_co_2_bep_4_ban(self):
        with Workdir() as w:
            out = w.path("o.jsonl")
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "1", "--out", out)
            self.assertEqual(code, 0, err)
            s0 = snapshots(read_jsonl(out))[0]
        self.assertEqual([s["id"] for s in s0["stoves"]], ["B1", "B2"])
        self.assertEqual([t["id"] for t in s0["tables"]], ["T1", "T2", "T3", "T4"])
        self.assertTrue(all(t["customer_id"] is None for t in s0["tables"]))


class Menu(unittest.TestCase):
    def test_sau_mon_dung_spec(self):
        menu = TUNING["menu"]
        self.assertEqual(sorted(menu), sorted(MENU))
        for dish, (recipe, cook_s, price) in MENU.items():
            self.assertEqual(menu[dish], {"recipe": recipe, "cook_s": cook_s, "price": price}, dish)


class DayPlan(unittest.TestCase):
    def test_nam_ngay_khop_bang_spec(self):
        plan = TUNING["day_plan"]
        self.assertEqual([p["day"] for p in plan], [1, 2, 3, 4, 5])
        for p in plan:
            dishes, ingredients = PLAN[p["day"]]
            self.assertEqual(p["dishes"], dishes)
            self.assertEqual(p["ingredients"], ingredients)

    def test_ingredients_bang_tong_cong_thuc_nhan_suat(self):
        for p in TUNING["day_plan"]:
            total = {}
            for dish, qty in p["dishes"].items():
                for ing, n in TUNING["menu"][dish]["recipe"].items():
                    total[ing] = total.get(ing, 0) + n * qty
            self.assertEqual(p["ingredients"], total, f"D{p['day']}")
            self.assertEqual(list(p["ingredients"]), sorted(p["ingredients"]))


class Inventory(unittest.TestCase):
    def test_kho_co_ca_keo_keo_neo(self):
        with Workdir() as w:
            inv = write_json(w.path("inv.json"), {"items": {"ca_keo": 2, "keo_neo": 1}})
            out = w.path("o.jsonl")
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "1",
                                     "--inventory", inv, "--out", out)
            self.assertEqual(code, 0, err)
            s0 = snapshots(read_jsonl(out))[0]
        self.assertEqual(s0["stock"], {"ca_keo": 2, "keo_neo": 1})

    def test_scenario_stock_co_ca_keo_keo_neo(self):
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"quan": {"stock": {"ca_keo": 2, "keo_neo": 1}}})
            out = w.path("o.jsonl")
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "1",
                                     "--scenario", sc, "--out", out)
            self.assertEqual(code, 0, err)
            s0 = snapshots(read_jsonl(out))[0]
        self.assertEqual(s0["stock"], {"ca_keo": 2, "keo_neo": 1})

    def test_kind_la_van_exit_2(self):
        with Workdir() as w:
            inv = write_json(w.path("inv.json"), {"items": {"ca_la": 1}})
            code, _ = run_headless("--mode", "quan", "--seed", "1", "--ticks", "1",
                                   "--inventory", inv, "--out", w.path("o.jsonl"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
