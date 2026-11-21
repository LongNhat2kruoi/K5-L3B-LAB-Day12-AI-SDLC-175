"""Quán lát 4: bếp, interact, bưng, phục vụ, trả tiền, boa, uy tín."""

import copy
import unittest
from fractions import Fraction

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.quan import QuanSim
from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, stock_items, write_json

DISH = "goi_bong_sung"
STOVE = [2, 8]
TABLE = [9, 2]
PAYLOAD = {"order_id": "C1", "dish_id": DISH, "base_price": 40}


def run(block, ticks, fr=None, seed=1):
    block = dict({"random_customers": False}, **block)
    with Workdir() as w:
        args = ["--mode", "quan", "--seed", str(seed), "--ticks", str(ticks),
                "--scenario", write_json(w.path("sc.json"), {"quan": block}), "--out", w.path("o.jsonl")]
        if fr is not None:
            args += ["--inputs", write_json(w.path("in.json"), frames(*fr))]
        code, err = run_headless(*args)
        assert code == 0, err
        return read_jsonl(w.path("o.jsonl"))


def cust(**kw):
    c = {"id": "C1", "table_id": "T1", "dish_id": DISH}
    c.update(kw)
    return c


def press(tick):
    return {"tick": tick, "interact": True}


def release(tick):
    return {"tick": tick, "interact": False}


def at_stove(**kw):
    return dict({"player": {"pos": STOVE}, "customers": [cust()], "stock": stock_items({"bong_sung": 2})}, **kw)


def at_table(**kw):
    block = {"player": {"pos": TABLE}, "hand": dict(PAYLOAD),
             "customers": [cust(order_status="assigned", base_price=40)]}
    block.update(kw)
    return block


def acted(rows):
    return [e["name"] for e in events(rows) if e["name"] in ("cook_started", "dish_picked", "served")]


def two_table_sim(block):
    t = copy.deepcopy(load_contract()["tuning"])
    t["quan"]["tables"].append({"id": "T2", "pos": [12, 2]})
    return QuanSim(t, dict({"random_customers": False}, **block), Streams(1), IdAllocator())


def press_step(sim):
    return sim.step(InputState((0.0, 0.0), {}, {"interact"}))


class Cook(unittest.TestCase):
    def test_cook_ready_pick_flow(self):
        rows = run(at_stove(), 400, [press(9), release(10), press(300)])
        cs = events(rows, "cook_started")
        self.assertEqual(len(cs), 1)
        t0 = cs[0]["tick"]
        # nấu ở tick t0 (bấm ở tick 9): 2 cá thể đã hao t0 tick * 1/240 => tươi 100 - t0/240 (xuất làm tròn 3 số lẻ);
        # giá chốt theo tươi: floor(40 * tươi / 100) = 39
        fresh = round(float(Fraction(100) - Fraction(t0, 240)), 3)
        self.assertEqual(cs[0]["data"], {"stove_id": "B1", "order_id": "C1", "dish_id": DISH,
                                         "items": [{"id": "I1", "kind": "bong_sung", "fresh": fresh},
                                                   {"id": "I2", "kind": "bong_sung", "fresh": fresh}],
                                         "base_price": 39})
        snap = [s for s in snapshots(rows) if s["tick"] == t0][0]
        self.assertEqual(snap["stock"], [])
        self.assertEqual(snap["customers"][0]["order_status"], "assigned")
        self.assertEqual(snap["customers"][0]["reserved"], [])
        self.assertEqual(snap["stoves"][0]["state"], "cooking")
        dr = events(rows, "dish_ready")
        self.assertEqual([e["tick"] for e in dr], [t0 + 240])
        self.assertEqual(dr[0]["data"], {"stove_id": "B1", "order_id": "C1", "dish_id": DISH})
        dp = events(rows, "dish_picked")
        self.assertEqual(len(dp), 1)
        self.assertEqual(dp[0]["data"], {"stove_id": "B1", "order_id": "C1", "dish_id": DISH})
        last = snapshots(rows)[-1]
        self.assertEqual(last["hand"], dict(PAYLOAD, base_price=39))
        self.assertEqual(last["stoves"][0]["state"], "idle")
        self.assertIsNone(last["stoves"][0]["dish"])

    def test_ready_ticks_dem_tu_buoc_sau(self):
        rows = run(at_stove(), 280, [press(9)])
        t0 = events(rows, "cook_started")[0]["tick"]
        stove = {s["tick"]: s["stoves"][0] for s in snapshots(rows)}
        self.assertEqual((stove[t0 + 240]["state"], stove[t0 + 240]["ready_ticks"]), ("ready", 0))
        self.assertEqual(stove[t0 + 250]["ready_ticks"], 10)

    def test_bep_idle_khong_co_don_reserved_bo_luot(self):
        rows = run({"player": {"pos": STOVE}}, 10, [press(3)])
        self.assertEqual(acted(rows), [])

    def test_tay_day_bep_ready_bo_luot(self):
        d2 = {"order_id": "C2", "dish_id": DISH, "base_price": 40}
        sim = two_table_sim({"player": {"pos": STOVE}, "hand": dict(PAYLOAD),
                             "customers": [cust(order_status="assigned"),
                                           cust(id="C2", table_id="T2", order_status="assigned")],
                             "stoves": [{"id": "B1", "state": "ready", "dish": d2}]})
        self.assertEqual(press_step(sim), [])
        self.assertEqual(sim.hand, PAYLOAD)
        self.assertEqual(sim.stoves[0]["state"], "ready")

    def test_khach_roi_khi_mon_dang_nau(self):
        rows = run(at_stove(customers=[cust(patience_ticks_left=100)]), 200, [press(5)])
        t0 = events(rows, "cook_started")[0]["tick"]
        left = events(rows, "customer_left")
        self.assertEqual(len(left), 1)
        self.assertGreater(left[0]["tick"], t0)
        last = snapshots(rows)[-1]
        self.assertEqual(last["stoves"][0]["state"], "idle")
        self.assertIsNone(last["stoves"][0]["dish"])
        self.assertEqual(last["stock"], [])  # nguyên liệu đã trừ, không hoàn
        self.assertEqual(events(rows, "dish_ready"), [])


class Nearest(unittest.TestCase):
    """Người chơi ở [5,5]; bếp B1 và bàn T1 đặt lại quanh đó. Bếp ready giữ món C1, tay trống."""

    @staticmethod
    def block(stove_pos, table_pos, ready):
        stove = {"id": "B1", "pos": stove_pos}
        if ready:
            stove.update(state="ready", dish=dict(PAYLOAD))
        status = "assigned" if ready else "reserved"
        return {"player": {"pos": [5.0, 5.0]}, "stock": stock_items({"bong_sung": 2}),
                "customers": [cust(order_status=status)],
                "stoves": [stove], "tables": [{"id": "T1", "pos": table_pos}]}

    def test_bep_gan_hon_chon_bep(self):
        rows = run(self.block([5.5, 5.0], [6.0, 5.0], ready=False), 5, [press(2)])
        self.assertEqual(acted(rows), ["cook_started"])

    def test_cung_khoang_cach_bep_truoc_ban(self):
        rows = run(self.block([6.0, 5.0], [4.0, 5.0], ready=True), 5, [press(2)])
        self.assertEqual(acted(rows), ["dish_picked"])

    def test_gan_nhat_la_ban_khong_lam_duoc_thi_bo_luot(self):
        # bàn gần hơn bếp nhưng tay trống; bếp ready xa hơn không được thử thay
        rows = run(self.block([6.0, 5.0], [5.5, 5.0], ready=True), 5, [press(2)])
        self.assertEqual(acted(rows), [])

    def test_ngoai_ban_kinh_khong_tuong_tac(self):
        rows = run(self.block([6.6, 5.0], [5.0, 6.6], ready=False), 5, [press(2)])  # cách 1.6 > 1.5
        self.assertEqual(acted(rows), [])

    def test_dung_ban_kinh_la_tuong_tac(self):
        rows = run(self.block([6.5, 5.0], [5.0, 6.6], ready=False), 5, [press(2)])  # cách đúng 1.5
        self.assertEqual(acted(rows), ["cook_started"])


class Serve(unittest.TestCase):
    def test_served_co_boa_khi_kien_nhan_day(self):
        rows = run(at_table(), 10, [press(2)])
        sv = events(rows, "served")
        self.assertEqual(len(sv), 1)
        d = sv[0]["data"]
        self.assertGreaterEqual(d["patience_ticks_left"], 1800)
        self.assertEqual(d, {"order_id": "C1", "table_id": "T1", "dish_id": DISH,
                             "patience_ticks_left": d["patience_ticks_left"], "base_price": 40, "tip": 8})
        last = snapshots(rows)[-1]
        self.assertIsNone(last["hand"])
        c = last["customers"][0]
        self.assertEqual((c["state"], c["order_status"], c["tip"]), ("eating", "served", 8))
        self.assertGreater(c["eat_ticks_left"], 0)

    def test_khong_boa_khi_kien_nhan_duoi_nguong(self):
        block = at_table()
        block["customers"][0]["patience_ticks_left"] = 1500
        rows = run(block, 10, [press(2)])
        self.assertEqual(events(rows, "served")[0]["data"]["tip"], 0)

    def test_phuc_vu_sai_khach_bo_luot(self):
        sim = two_table_sim({"player": {"pos": TABLE},
                             "hand": {"order_id": "C2", "dish_id": DISH, "base_price": 40},
                             "customers": [cust(order_status="reserved"),
                                           cust(id="C2", table_id="T2", order_status="assigned", base_price=40)],
                             "stock": stock_items({"bong_sung": 2})})
        self.assertEqual(press_step(sim), [])
        self.assertEqual(sim.hand["order_id"], "C2")


class Pay(unittest.TestCase):
    def test_tra_tien_sau_600_tick(self):
        rows = run(at_table(), 700, [press(2)])
        t0 = events(rows, "served")[0]["tick"]
        paid = events(rows, "paid")
        self.assertEqual([e["tick"] for e in paid], [t0 + 600])
        self.assertEqual(paid[0]["data"], {"order_id": "C1", "table_id": "T1", "base_price": 40, "tip": 8,
                                           "amount": 48, "reason": "finished_eating"})
        self.assertEqual(snapshots(rows)[-1]["customers"], [])
        self.assertEqual(events(rows, "quan_end"), [])

    def test_tien_va_uy_tin_cong_boa(self):
        rows = run(at_table(time_left_ticks=640), 700, [press(2)])
        end = events(rows, "quan_end")[0]["data"]
        self.assertEqual((end["money"], end["earned"], end["shift_earned"]), (48, 48, 48))
        self.assertAlmostEqual(end["reputation"], 3.2)

    def test_khong_boa_khong_doi_uy_tin(self):
        block = at_table(time_left_ticks=640)
        block["customers"][0]["patience_ticks_left"] = 1500
        rows = run(block, 700, [press(2)])
        d = events(rows, "paid")[0]["data"]
        self.assertEqual((d["tip"], d["amount"]), (0, 40))
        end = events(rows, "quan_end")[0]["data"]
        self.assertEqual(end["money"], 40)
        self.assertAlmostEqual(end["reputation"], 3.0)

    def test_het_ca_khi_dang_an(self):
        rows = run(at_table(time_left_ticks=100), 200, [press(2)])
        paid = events(rows, "paid")
        self.assertEqual([(e["tick"], e["data"]["reason"], e["data"]["amount"]) for e in paid],
                         [(100, "closing", 48)])
        names = [r["name"] for r in rows if r["type"] == "event" and r["tick"] == 100]
        self.assertEqual(names, ["paid", "quan_end"])
        self.assertEqual(events(rows, "quan_end")[0]["data"]["money"], 48)

    def test_tat_dinh(self):
        fr = [press(9), release(10), press(300)]
        self.assertEqual(run(at_stove(), 400, fr), run(at_stove(), 400, fr))


if __name__ == "__main__":
    unittest.main()
