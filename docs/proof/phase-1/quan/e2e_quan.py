"""Kiểm chứng toàn quy trình quán: smoke 2 tiến trình (mục G) + một ca quán chơi bằng input thật.

Chạy từ gốc repo: python3 <this> <out_dir>
"""
import filecmp
import json
import math
import os
import subprocess
import sys

sys.path.insert(0, os.getcwd())
from chonoi.contract import load_contract  # noqa: E402
from chonoi.inputs import InputState  # noqa: E402
from chonoi.runner import Session  # noqa: E402

OUT = os.path.abspath(sys.argv[1])
os.makedirs(OUT, exist_ok=True)
log = open(os.path.join(OUT, "e2e-log.txt"), "w", encoding="utf-8", newline="\n")


def say(*a):
    msg = " ".join(str(x) for x in a)
    print(msg)
    log.write(msg + "\n")


def run(*args):
    cmd = ["python3", "-m", "chonoi.headless", *args]
    p = subprocess.run(cmd, capture_output=True, text=True)
    say("$", "python3 -m chonoi.headless", " ".join(args), "->", p.returncode, p.stderr.strip())
    return p.returncode


def rows(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def dump(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    return path


ok = True


def check(cond, label):
    global ok
    ok &= bool(cond)
    say(("PASS " if cond else "FAIL ") + label)


# 1. Smoke hai tiến trình (PRD-0 mục G)
say("== 1. Smoke hai tiến trình gather -> quan ==")
dock = dump(os.path.join(OUT, "dock.json"), {"gather": {"hold": ["ca_loc", "bong_sung", "bong_sung"]}})
dinp = dump(os.path.join(OUT, "dock-inputs.json"), {"frames": [{"tick": 0, "interact": True}]})
catch = os.path.join(OUT, "catch.json")
g = os.path.join(OUT, "gather.jsonl")
q0 = os.path.join(OUT, "quan0.jsonl")
check(run("--mode", "gather", "--seed", "42", "--scenario", dock, "--inputs", dinp, "--ticks", "1",
          "--out", g, "--inventory-out", catch) == 0, "gather exit 0")
check(run("--mode", "quan", "--seed", "42", "--inventory", catch, "--ticks", "0", "--out", q0) == 0, "quan exit 0")
inv = json.load(open(catch, encoding="utf-8"))
snap0 = [r for r in rows(q0) if r["type"] == "snapshot"][0]
say("catch.json =", inv, "| quan stock tick0 =", snap0["stock"])
check(snap0["stock"] == {"bong_sung": 2, "ca_loc": 1} == inv["items"], "quán nhận đúng file kho")

# 2. Một ca quán đầy đủ, bot tự chơi -> sinh inputs -> chạy headless 2 lần
say("== 2. Ca quán đầy đủ bằng input thật (bot) ==")
tuning = load_contract()["tuning"]
q = tuning["quan"]
stock_inv = dump(os.path.join(OUT, "kho-quan.json"),
                 {"items": {"bong_sung": 6, "ca_loc": 2, "ca_linh": 3, "bong_dien_dien": 1}})
inventory = {"bong_sung": 6, "ca_loc": 2, "ca_linh": 3, "bong_dien_dien": 1}
SEED, TICKS = 7, int(q["duration_s"] * 60) + 5
sess = Session("quan", tuning, {}, SEED, inventory)
stove = q["stoves"][0]["pos"]
table = q["tables"][0]["pos"]
R = q["interact_radius"]
frames, held, last_move = [], False, None


def plan():
    s = sess.sim
    stv = s.stoves[0]
    if s.hand:
        return table
    if stv["state"] == "ready":
        return stove
    if stv["state"] == "idle" and any(c["order_status"] == "reserved" for c in s.customers):
        return stove
    return None  # chờ


while not sess.done and sess.tick < TICKS:
    target = plan()
    pos = sess.sim.pos
    move, press = [0, 0], False
    if target is not None:
        d = math.dist(pos, target)
        if d <= R - 0.3:
            press = True
        else:
            move = [round((target[0] - pos[0]) / d, 3), round((target[1] - pos[1]) / d, 3)]
    fr = {"tick": sess.tick}
    if move != last_move:
        fr["move"] = move
        last_move = move
    want = press and not held  # cạnh lên
    if want or held:
        fr["interact"] = want
        held = want
    if len(fr) > 1:
        frames.append(fr)
    edges = {"interact"} if want else set()
    sess.step(InputState(tuple(move), {"interact": held, "catch": False}, edges))

inp = dump(os.path.join(OUT, "quan-inputs.json"), {"frames": frames})
outs = []
for i in (1, 2):
    o = os.path.join(OUT, f"quan-ca-{i}.jsonl")
    check(run("--mode", "quan", "--seed", str(SEED), "--inventory", stock_inv, "--inputs", inp,
              "--ticks", str(TICKS), "--out", o) == 0, f"ca quán lần {i} exit 0")
    outs.append(o)
check(filecmp.cmp(outs[0], outs[1], shallow=False), "cùng seed + input -> JSONL giống từng byte")

rs = rows(outs[0])
ev = [r for r in rs if r["type"] == "event"]
names = [e["name"] for e in ev]
say("Chuỗi event:")
for e in ev:
    say(f"  tick {e['tick']:>5} {e['name']:<16} {json.dumps(e['data'], ensure_ascii=False)}")
end = rs[-1]
say("end =", json.dumps(end, ensure_ascii=False))
for n in ("customer_arrived", "cook_started", "dish_ready", "dish_picked", "served", "paid", "quan_end"):
    check(n in names, f"có event {n}")
check(names[-1] == "quan_end" and end["type"] == "end" and end["reason"] == "time", "kết ca bằng quan_end, end reason time")
paid = [e["data"] for e in ev if e["name"] == "paid"]
total = sum(p["amount"] for p in paid)
check(end["money"] == end["earned"] == total, f"money = earned = tổng paid ({total})")
check(all(p["amount"] == p["base_price"] + p["tip"] for p in paid), "amount = base_price + tip")
check(end["score"] == end["earned"] + 100 * math.floor(end["reputation"]), "score = earned + 100*floor(reputation)")
first = next(e for e in ev if e["name"] == "customer_arrived")
check(first["tick"] == q["first_customer_tick"], f"khách đầu ở tick {q['first_customer_tick']}")
say("KẾT QUẢ:", "TẤT CẢ ĐẠT" if ok else "CÓ MỤC CHƯA ĐẠT")
log.close()
sys.exit(0 if ok else 1)
