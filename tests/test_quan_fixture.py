"""Fixture quán (PRD-0 mục D): schema, dựng trạng thái mặc định, mâu thuẫn -> mã 2."""

import unittest

from helpers import Workdir, read_jsonl, run_headless, snapshots, write_json

DISH = "ca_loc_nuong_trui"
LAU = "lau_ca_linh_dien_dien"
CUSTOMER_KEYS = {"id", "table_id", "dish_id", "order_tick", "state", "patience_ticks_left",
                 "eat_ticks_left", "order_status", "reserved", "base_price", "tip"}


def cust(**kw):
    c = {"id": "C1", "table_id": "T1", "dish_id": DISH}
    c.update(kw)
    return c


def payload(order_id="C1", dish_id=DISH, base_price=60):
    return {"order_id": order_id, "dish_id": dish_id, "base_price": base_price}


def run(block, ticks=0):
    """Trả (mã thoát, các dòng JSONL)."""
    with Workdir() as w:
        sc = write_json(w.path("sc.json"), {"quan": block})
        out = w.path("o.jsonl")
        code, _ = run_headless("--mode", "quan", "--seed", "1", "--ticks", str(ticks), "--scenario", sc, "--out", out)
        try:
            return code, read_jsonl(out)
        except OSError:
            return code, []


class Contradictions(unittest.TestCase):
    def assert_rejected(self, block):
        code, rows = run(block)
        self.assertEqual(code, 2, block)
        self.assertEqual(rows, [], block)

    def test_khach_khoa_la(self):
        self.assert_rejected({"stock": {"ca_loc": 1}, "customers": [cust(mood="vui")]})

    def test_dish_id_la_hoac_thieu(self):
        self.assert_rejected({"stock": {"ca_loc": 1}, "customers": [cust(dish_id="pho")]})
        self.assert_rejected({"customers": [{"id": "C1", "table_id": "T1"}]})

    def test_state_la(self):
        self.assert_rejected({"stock": {"ca_loc": 1}, "customers": [cust(state="sleeping")]})

    def test_giu_khac_cong_thuc(self):
        self.assert_rejected({"stock": {"ca_loc": 5}, "customers": [cust(reserved={"ca_loc": 2})]})

    def test_giu_qua_ton(self):
        self.assert_rejected({"stock": {}, "customers": [cust()]})
        self.assert_rejected({"stock": {"ca_loc": 1}, "tables": [{"id": "T1"}],
                              "customers": [cust(), cust(id="C2", table_id="T2")]})

    def test_assigned_khong_mon(self):
        self.assert_rejected({"customers": [cust(order_status="assigned", reserved={})]})

    def test_bep_va_tay_cung_don(self):
        self.assert_rejected({"customers": [cust(order_status="assigned")], "hand": payload(),
                              "stoves": [{"id": "B1", "state": "ready", "dish": payload()}]})

    def test_payload_tro_khach_khong_co(self):
        self.assert_rejected({"hand": payload("C9")})

    def test_payload_tro_don_khong_assigned(self):
        self.assert_rejected({"stock": {"ca_loc": 1}, "customers": [cust()], "hand": payload()})

    def test_payload_khac_dish_id(self):
        self.assert_rejected({"customers": [cust(order_status="assigned")],
                              "hand": payload(dish_id="goi_bong_sung", base_price=40)})

    def test_bep_cooking_timer_0(self):
        self.assert_rejected({"customers": [cust(order_status="assigned")],
                              "stoves": [{"id": "B1", "state": "cooking", "dish": payload(), "cook_ticks_left": 0}]})

    def test_bep_idle_con_dish(self):
        self.assert_rejected({"customers": [cust(order_status="assigned")],
                              "stoves": [{"id": "B1", "state": "idle", "dish": payload()}]})

    def test_eating_thieu_base_price(self):
        self.assert_rejected({"customers": [cust(state="eating", order_status="served", eat_ticks_left=30,
                                                 tip=0)]})

    def test_served_khong_eating(self):
        self.assert_rejected({"customers": [cust(order_status="served", base_price=60, tip=0)]})

    def test_waiting_eat_ticks_khac_0(self):
        self.assert_rejected({"stock": {"ca_loc": 1}, "customers": [cust(eat_ticks_left=5)]})

    def test_payload_dish_id_khong_phai_chuoi(self):
        self.assert_rejected({"hand": payload(dish_id=[])})

    def test_boolean_khong_phai_so(self):
        eating = dict(state="eating", order_status="served", eat_ticks_left=30)
        self.assert_rejected({"customers": [cust(base_price=60, tip=True, **eating)]})
        self.assert_rejected({"customers": [cust(base_price=True, tip=0, **eating)]})
        self.assert_rejected({"hand": payload(base_price=True)})
        self.assert_rejected({"reputation": True})

    def test_reputation_ngoai_mien(self):
        self.assert_rejected({"reputation": 5.5})
        self.assert_rejected({"reputation": -1})

    def test_random_customers_khong_bool(self):
        self.assert_rejected({"random_customers": 1})


class ValidFixtures(unittest.TestCase):
    def test_khach_thieu_reserved_duoc_cap_dung_cong_thuc(self):
        code, rows = run({"stock": {"ca_linh": 3, "bong_dien_dien": 1},
                          "customers": [cust(dish_id=LAU)]})
        self.assertEqual(code, 0)
        c = snapshots(rows)[0]["customers"][0]
        self.assertEqual(set(c), CUSTOMER_KEYS)
        self.assertEqual(c["reserved"], {"bong_dien_dien": 1, "ca_linh": 3})
        self.assertEqual((c["state"], c["order_tick"], c["patience_ticks_left"], c["eat_ticks_left"],
                          c["order_status"], c["base_price"], c["tip"]),
                         ("waiting", 0, 3600, 0, "reserved", None, None))

    def test_bo_khoa_luong_0_trong_reserved(self):
        code, rows = run({"stock": {"ca_loc": 1}, "customers": [cust(reserved={"ca_loc": 1, "ca_linh": 0})]})
        self.assertEqual(code, 0)
        self.assertEqual(snapshots(rows)[0]["customers"][0]["reserved"], {"ca_loc": 1})

    def test_assigned_co_mon_o_bep(self):
        code, rows = run({"customers": [cust(order_status="assigned")],
                          "stoves": [{"id": "B1", "state": "cooking", "dish": payload(), "cook_ticks_left": 10}]})
        self.assertEqual(code, 0)
        self.assertEqual(snapshots(rows)[0]["customers"][0]["reserved"], {})

    def test_khach_eating_hop_le(self):
        code, _ = run({"customers": [cust(state="eating", order_status="served", eat_ticks_left=30,
                                          base_price=60, tip=12)]})
        self.assertEqual(code, 0)

    def test_khong_khach_ticks_0(self):
        code, rows = run({})
        self.assertEqual(code, 0)
        self.assertEqual(snapshots(rows)[0]["customers"], [])

    def test_player_snapshot_co_vel(self):
        code, rows = run({"player": {"pos": [8, 5], "vel": [1.5, 0]}})
        self.assertEqual(code, 0)
        self.assertEqual(snapshots(rows)[0]["player"], {"pos": [8, 5], "vel": [1.5, 0.0]})


if __name__ == "__main__":
    unittest.main()
