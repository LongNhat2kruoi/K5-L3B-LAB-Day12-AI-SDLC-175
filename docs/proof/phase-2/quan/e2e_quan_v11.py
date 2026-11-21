"""Phase 2 (TICKET-02) — kiểm chứng quán v1.1: smoke tích hợp gather->quan, một ca 4 bàn/2 bếp chơi bằng input thật.

Chạy từ gốc repo: python3 e2e_quan_v11.py <out_dir>
"""
import filecmp
import json
import math
import os
import subprocess
import sys

sys.path.insert(0, os.getcwd())
from chonoi.contract import load_contract  # noqa: E402
from chonoi.ids import id_key  # noqa: E402
from chonoi.inputs import InputState  # noqa: E402
from chonoi.runner import Session  # noqa: E402

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


def run(*args):
    p = subprocess.run(["python3", "-m", "chonoi.headless", *args], capture_output=True, text=True)
    shown = [os.path.basename(a) if os.path.isabs(a) else a for a in args]
    say("$ python3 -m chonoi.headless", " ".join(shown), "->", p.returncode, p.stderr.strip())
    return p.returncode


def rows(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def dump(name, obj):
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    return p


tuning = load_contract()["tuning"]
q, menu = tuning["quan"], tuning["menu"]

say("== 0. Dữ liệu v1.1 ==")
check([s["id"] for s in q["stoves"]] == ["B1", "B2"], "2 bếp B1, B2")
check([t["id"] for t in q["tables"]] == ["T1", "T2", "T3", "T4"], "4 bàn T1-T4")
check(len(menu) == 6, "6 món")
for d in tuning["day_plan"]:
    need = {}
    for dish, n in d["dishes"].items():
        for k, v in menu[dish]["recipe"].items():
            need[k] = need.get(k, 0) + v * n
    check(need == d["ingredients"], f"D{d['day']} ingredients = tổng công thức × suất {d['ingredients']}")

say("== 1. Smoke tích hợp gather --inventory-out -> quan --inventory ==")
dock = dump("dock.json", {"gather": {"hold": ["ca_loc", "bong_sung", "bong_sung"]}})
dinp = dump("dock-inputs.json", {"frames": [{"tick": 0, "interact": True}]})
catch = os.path.join(OUT, "catch.json")
check(run("--mode", "gather", "--seed", "42", "--scenario", dock, "--inputs", dinp, "--ticks", "1",
          "--out", os.path.join(OUT, "gather.jsonl"), "--inventory-out", catch) == 0, "gather exit 0")
check(run("--mode", "quan", "--seed", "42", "--inventory", catch, "--ticks", "0",
          "--out", os.path.join(OUT, "quan0.jsonl")) == 0, "quan exit 0")
inv = json.load(open(catch, encoding="utf-8"))
s0 = [r for r in rows(os.path.join(OUT, "quan0.jsonl")) if r["type"] == "snapshot"][0]
say("catch.json =", inv, "| quan stock tick0 =", s0["stock"])
check(s0["stock"] == inv["items"] == {"bong_sung": 2, "ca_loc": 1}, "quán nhận đúng file kho")
check(len(s0["stoves"]) == 2 and len(s0["tables"]) == 4, "snapshot tick 0 có 2 bếp, 4 bàn")

say("== 2. Ca quán 4 bàn/2 bếp bằng input thật (bot) ==")
items = {"ca_loc": 4, "ca_linh": 5, "bong_dien_dien": 4, "bong_sung": 4, "ca_keo": 5, "keo_neo": 1}
kho = dump("kho-quan.json", {"items": items})
SEED, TICKS = 11, int(q["duration_s"] * 60) + 5
sess = Session("quan", tuning, {}, SEED, dict(items))
R = q["interact_radius"]
frames, held, last_move = [], False, None


def target():
    s = sess.sim
    pos = s.pos
    if s.hand:
        c = next(c for c in s.customers if c["id"] == s.hand["order_id"])
        return next(t["pos"] for t in s.tables if t["id"] == c["table_id"])
    ready = [st for st in s.stoves if st["state"] == "ready"]
    if ready:
        return min(ready, key=lambda st: (math.dist(pos, st["pos"]), id_key(st["id"])))["pos"]
    idle = [st for st in s.stoves if st["state"] == "idle"]
    if idle and any(c["order_status"] == "reserved" for c in s.customers):
        return min(idle, key=lambda st: (math.dist(pos, st["pos"]), id_key(st["id"])))["pos"]
    return None


while not sess.done and sess.tick < TICKS:
    tgt, pos = target(), sess.sim.pos
    move, press = [0, 0], False
    if tgt is not None:
        d = math.dist(pos, tgt)
        if d <= R - 0.4:
            press = True
        else:
            move = [round((tgt[0] - pos[0]) / d, 3), round((tgt[1] - pos[1]) / d, 3)]
    fr = {"tick": sess.tick}
    if move != last_move:
        fr["move"], last_move = move, move
    want = press and not held
    if want or held:
        fr["interact"], held = want, want
    if len(fr) > 1:
        frames.append(fr)
    sess.step(InputState(tuple(move), {"interact": held, "catch": False}, {"interact"} if want else set()))

inp = dump("quan-inputs.json", {"frames": frames})
outs = []
for i in (1, 2):
    o = os.path.join(OUT, f"quan-ca-{i}.jsonl")
    check(run("--mode", "quan", "--seed", str(SEED), "--inventory", kho, "--inputs", inp, "--ticks", str(TICKS),
              "--out", o) == 0, f"ca quán lần {i} exit 0")
    outs.append(o)
check(filecmp.cmp(*outs, shallow=False), "cùng seed + input -> JSONL giống từng byte")
rs = rows(outs[0])
ev = [r for r in rs if r["type"] == "event"]
say("Chuỗi event:")
for e in ev:
    say(f"  tick {e['tick']:>5} {e['name']:<16} {json.dumps(e['data'], ensure_ascii=False)}")
end = rs[-1]
say("end =", json.dumps(end, ensure_ascii=False))
names = [e["name"] for e in ev]
arr = [e["data"] for e in ev if e["name"] == "customer_arrived"]
check({a["table_id"] for a in arr} > {"T1"}, f"khách ngồi nhiều bàn: {sorted({a['table_id'] for a in arr})}")
check(set(a["dish_id"] for a in arr) <= set(menu), "món khách gọi thuộc menu 6 món")
new = {"canh_chua_ca_loc", "ca_keo_nuong", "lau_mam"}
check(bool(new & {a["dish_id"] for a in arr}), f"có khách gọi món mới: {sorted(new & {a['dish_id'] for a in arr})}")
for e in ev:
    if e["name"] == "cook_started":
        dsh = menu[e["data"]["dish_id"]]
        exp = sorted(k for k, v in dsh["recipe"].items() for _ in range(v))
        if e["data"]["items"] != exp or e["data"]["base_price"] != dsh["price"]:
            check(False, f"cook_started khớp menu: {e['data']}")
check(True, "mọi cook_started có items/base_price khớp menu")
paid = [e["data"] for e in ev if e["name"] == "paid"]
check(end["money"] == end["earned"] == sum(p["amount"] for p in paid), f"money = earned = tổng paid ({end['earned']})")
check(end["score"] == end["earned"] + 100 * math.floor(end["reputation"]), "score = earned + 100*floor(rep)")
check(names[-1] == "quan_end" and end["reason"] == "time", "kết ca quan_end, reason time")

say("== 3. Hai bếp nấu song song (2 khách chờ sẵn ở T1, T2) ==")
sc = dump("hai-bep.json", {"quan": {"player": {"pos": [3.5, 7.5]}, "random_customers": False,
                                     "stock": {"ca_loc": 1, "ca_keo": 2},
                                     "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"},
                                                   {"id": "C2", "table_id": "T2", "dish_id": "ca_keo_nuong"}]}})
hb = dump("hai-bep-inputs.json", {"frames": [{"tick": 0, "move": [-1, 0]}, {"tick": 10, "move": [0, 0], "interact": True},
                                             {"tick": 11, "interact": False}, {"tick": 12, "move": [1, 0]},
                                             {"tick": 40, "move": [0, 0], "interact": True}, {"tick": 41, "interact": False}]})
o3 = os.path.join(OUT, "hai-bep.jsonl")
check(run("--mode", "quan", "--seed", "1", "--scenario", sc, "--inputs", hb, "--ticks", "60", "--out", o3) == 0, "exit 0")
cs = [e for e in rows(o3) if e["type"] == "event" and e["name"] == "cook_started"]
for e in cs:
    say(f"  tick {e['tick']} cook_started {json.dumps(e['data'], ensure_ascii=False)}")
check([e["data"]["stove_id"] for e in cs] == ["B1", "B2"] and [e["data"]["order_id"] for e in cs] == ["C1", "C2"],
      "B1 nấu đơn C1, B2 nấu đơn C2 (đơn reserved cũ nhất theo order_tick rồi id bàn)")
snap = [r for r in rows(o3) if r["type"] == "snapshot"][-1]
check([s["state"] for s in snap["stoves"]] == ["cooking", "cooking"], "hai bếp cùng đang nấu")
say("KẾT QUẢ:", "TẤT CẢ ĐẠT" if ok else "CÓ MỤC CHƯA ĐẠT")
log.close()
sys.exit(0 if ok else 1)
