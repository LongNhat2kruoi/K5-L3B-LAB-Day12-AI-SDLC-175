"""Phase 3 (TICKET-03) — kiểm chứng quán v1.2 (kho cá thể, độ tươi) trong tiến trình với contract bật freshness.

Repo vẫn ở schema đếm; script dựng tuning v1.2 = tuning repo + freshness (đúng giá trị TICKET-03).
Chạy từ gốc repo: python3 e2e_quan_v12.py <out_dir>
"""
import copy
import filecmp
import json
import math
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.getcwd())
from chonoi.contract import load_contract  # noqa: E402
from chonoi.errors import BadInput  # noqa: E402
from chonoi.ids import id_key  # noqa: E402
from chonoi.inputs import InputState  # noqa: E402
from chonoi.inventory import read_inventory, write_inventory  # noqa: E402
from chonoi.runner import Session, run  # noqa: E402

OUT = os.path.abspath(sys.argv[1])
os.makedirs(OUT, exist_ok=True)
log = open(os.path.join(OUT, "e2e-log.txt"), "w", encoding="utf-8", newline="\n")
ok = True


def say(*a):
    msg = " ".join(str(x) for x in a)
    print(msg)
    log.write(msg + "\n")


def check(cond, label):
    global ok
    ok &= bool(cond)
    say(("PASS " if cond else "FAIL ") + label)


def rows(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


base = load_contract()["tuning"]
t12 = copy.deepcopy(base)
t12["freshness"] = {"initial": 100, "gather_decay_per_s": 0.5, "quan_decay_per_s": 0.25, "spoiled_below": 30}
q, menu = t12["quan"], t12["menu"]
say("contract repo:", load_contract()["contract_version"], "| e2e dùng tuning + freshness", t12["freshness"])

say("== 1. File kho v1.2: ghi -> đọc giữ id, kind, fresh và nhánh ngưỡng 30 ==")
items = [{"id": "I10", "kind": "ca_linh", "fresh": Fraction(7199, 240)},   # 29.99583 < 30 (ươn)
         {"id": "I2", "kind": "ca_loc", "fresh": Fraction(30)},            # đúng 30
         {"id": "I3", "kind": "ca_linh", "fresh": Fraction(7201, 240)},    # 30.00417
         {"id": "I1", "kind": "bong_sung", "fresh": Fraction(195, 2)}]     # 97.5
kho = os.path.join(OUT, "kho-v12.json")
write_inventory(kho, items)
raw = json.load(open(kho, encoding="utf-8"))
say("file:", json.dumps(raw, ensure_ascii=False))
check([i["id"] for i in raw["items"]] == ["I1", "I2", "I3", "I10"], "file xuất theo id (I2 trước I10)")
back = {i["id"]: i for i in read_inventory(kho)}
check(all(back[i["id"]]["fresh"] == i["fresh"] and back[i["id"]]["kind"] == i["kind"] for i in items),
      "đọc lại đúng từng giá trị (chính xác tuyệt đối)")
check([back[k]["fresh"] < 30 for k in ("I10", "I2", "I3")] == [True, False, False], "nhánh ngưỡng 30 giữ nguyên")

say("== 2. Chọn schema theo phiên bản ==")
cnt = os.path.join(OUT, "kho-dem.json")
write_inventory(cnt, {"ca_loc": 1})
try:
    Session("quan", t12, {}, 1, read_inventory(cnt))
    check(False, "v1.2 từ chối kho đếm")
except BadInput as e:
    check(True, f"v1.2 từ chối kho đếm ({e})")
try:
    Session("quan", base, {}, 1, read_inventory(kho))
    check(False, "schema đếm từ chối kho cá thể")
except BadInput as e:
    check(True, f"schema đếm từ chối kho cá thể ({e})")

say("== 3. Ngưỡng ươn: fresh 30 -> spoiled ở tick 1; 7201/240 -> tick 2 ==")
sc = {"random_customers": False, "stock": [{"id": "I1", "kind": "ca_linh", "fresh": Fraction(30)},
                                          {"id": "I2", "kind": "ca_linh", "fresh": Fraction(7201, 240)}]}
o = os.path.join(OUT, "nguong.jsonl")
run("quan", t12, copy.deepcopy(sc), 1, [], 5, o, 1)
sp = [(e["tick"], e["data"]) for e in rows(o) if e["type"] == "event" and e["name"] == "spoiled"]
say("spoiled:", sp)
check(sp == [(1, {"item_id": "I1", "kind": "ca_linh", "location": "stock"}),
             (2, {"item_id": "I2", "kind": "ca_linh", "location": "stock"})], "spoiled đúng tick, đúng một lần mỗi cá thể")
s240 = [r for r in rows(o) if r["type"] == "snapshot"][-1]
say("stock tick 5:", s240["stock"])

say("== 4. Giữ chỗ vừa ươn -> nhả và giữ lại; giá theo tươi ==")
sc4 = {"random_customers": False, "player": {"pos": [2, 7.2]},
       "stock": [{"id": "I1", "kind": "ca_loc", "fresh": Fraction(30)},
                 {"id": "I2", "kind": "ca_loc", "fresh": Fraction(80)}],
       "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]}]}
o4 = os.path.join(OUT, "giu-lai.jsonl")
run("quan", t12, copy.deepcopy(sc4), 1, [{"tick": 5, "interact": True}], 7, o4, 1)
r4 = rows(o4)
ev4 = [(e["tick"], e["name"], e["data"]) for e in r4 if e["type"] == "event"]
for e in ev4:
    say("  ", e)
snap1 = next(r for r in r4 if r["type"] == "snapshot" and r["tick"] == 1)
check(snap1["customers"][0]["reserved"] == ["I2"], "tick 1: I1 ươn -> C1 giữ lại I2")
cs = next(d for _, n, d in ev4 if n == "cook_started")
exp_price = math.floor(60 * (Fraction(80) - Fraction(5, 240)) / 100)  # I2 hao 5 tick × 1/240
say("cook_started:", cs, "| giá kỳ vọng", exp_price)
check(cs["base_price"] == exp_price and [i["id"] for i in cs["items"]] == ["I2"], "nấu tiêu đúng id giữ, giá = floor(60 × fresh/100)")

say("== 5. Ca quán 10800 tick bằng bot, kho cá thể độ tươi lẫn lộn; tất định ==")
stock = []
kinds = [("ca_loc", 4), ("ca_linh", 5), ("bong_dien_dien", 4), ("bong_sung", 4), ("ca_keo", 5), ("keo_neo", 1)]
n = 1
for k, c in kinds:
    for j in range(c):
        stock.append({"id": f"I{n}", "kind": k, "fresh": Fraction(100 - 15 * (j % 4))})
        n += 1
kho5 = os.path.join(OUT, "kho-ca.json")
write_inventory(kho5, stock)
inv5 = read_inventory(kho5)
sess = Session("quan", t12, {}, 11, copy.deepcopy(inv5))
R, frames, held, last = q["interact_radius"], [], False, None


def target():
    s, pos = sess.sim, sess.sim.pos
    if s.hand:
        c = next(c for c in s.customers if c["id"] == s.hand["order_id"])
        return next(t["pos"] for t in s.tables if t["id"] == c["table_id"])
    rd = [st for st in s.stoves if st["state"] == "ready"]
    if rd:
        return min(rd, key=lambda st: (math.dist(pos, st["pos"]), id_key(st["id"])))["pos"]
    idle = [st for st in s.stoves if st["state"] == "idle"]
    if idle and any(c["order_status"] == "reserved" for c in s.customers):
        return min(idle, key=lambda st: (math.dist(pos, st["pos"]), id_key(st["id"])))["pos"]
    return None


TICKS = int(q["duration_s"] * 60) + 5
while not sess.done and sess.tick < TICKS:
    tg, pos = target(), sess.sim.pos
    mv, press = [0, 0], False
    if tg is not None:
        d = math.dist(pos, tg)
        if d <= R - 0.4:
            press = True
        else:
            mv = [round((tg[0] - pos[0]) / d, 3), round((tg[1] - pos[1]) / d, 3)]
    fr = {"tick": sess.tick}
    if mv != last:
        fr["move"], last = mv, mv
    want = press and not held
    if want or held:
        fr["interact"], held = want, want
    if len(fr) > 1:
        frames.append(fr)
    sess.step(InputState(tuple(mv), {"interact": held, "catch": False}, {"interact"} if want else set()))
with open(os.path.join(OUT, "quan-inputs.json"), "w", encoding="utf-8") as f:
    json.dump({"frames": frames}, f)
outs = []
for i in (1, 2):
    o5 = os.path.join(OUT, f"ca-v12-{i}.jsonl")
    run("quan", t12, {}, 11, frames, TICKS, o5, 10, inventory=read_inventory(kho5))
    outs.append(o5)
check(filecmp.cmp(*outs, shallow=False), "cùng seed + input + kho -> JSONL giống từng byte")
r5 = rows(outs[0])
ev5 = [e for e in r5 if e["type"] == "event"]
for e in ev5:
    if e["name"] in ("customer_arrived", "cook_started", "served", "paid", "no_dish", "spoiled", "quan_end"):
        say(f"  tick {e['tick']:>5} {e['name']:<16} {json.dumps(e['data'], ensure_ascii=False)}")
bad = []
for e in ev5:
    if e["name"] == "cook_started":
        d = e["data"]
        fresh = [Fraction(str(i["fresh"])) for i in d["items"]]
        price = menu[d["dish_id"]]["price"]
        lo = math.floor(price * (sum(fresh) / len(fresh) - Fraction(1, 1000)) / 100)
        hi = math.floor(price * (sum(fresh) / len(fresh) + Fraction(1, 1000)) / 100)
        if not (lo <= d["base_price"] <= hi) or d["items"] != sorted(d["items"], key=lambda i: (i["kind"], id_key(i["id"]))):
            bad.append(d)
check(not bad and any(e["name"] == "cook_started" for e in ev5),
      "mọi cook_started: giá = floor(giá × tươi TB/100), items sắp kind rồi id")
end = r5[-1]
paid = [e["data"] for e in ev5 if e["name"] == "paid"]
check(end["earned"] == sum(p["amount"] for p in paid) and end["score"] == end["earned"] + 100 * math.floor(end["reputation"]),
      f"earned = tổng paid ({end['earned']}), score = earned + 100×floor(rep) ({end['score']})")
last_snap = [r for r in r5 if r["type"] == "snapshot"][-1]
check(isinstance(last_snap["stock"], list) and all(set(i) == {"id", "kind", "fresh"} for i in last_snap["stock"]),
      "snapshot stock là mảng cá thể {id,kind,fresh}")
say("KẾT QUẢ:", "TẤT CẢ ĐẠT" if ok else "CÓ MỤC CHƯA ĐẠT")
log.close()
sys.exit(0 if ok else 1)
