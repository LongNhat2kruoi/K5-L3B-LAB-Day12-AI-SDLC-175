"""Benchmark có render thật (Contract v1.3): chạy client Pyxel 1280x720, cảnh sáng Ngày 1, Út Sen đứng yên.

Vẽ bằng đúng `play.main.Game.draw`; ở đây chỉ đo thời gian giữa hai lần vẽ liên tiếp.
"""

import argparse
import json
import math
import os
import sys
import time

WINDOW_SCALE = 4  # 320x180 x4 = 1280x720


def compute_metrics(frame_times, load_ms):
    """frame_times: thời gian (giây) của từng khung trong khoảng đo. Hàm thuần, không cần cửa sổ."""
    frames = len(frame_times)
    measured_s = sum(frame_times)
    avg_fps = frames / measured_s
    n = max(1, math.ceil(0.01 * frames))
    slowest = sorted(frame_times, reverse=True)[:n]
    p1_low_fps = 1.0 / (sum(slowest) / n)
    return {"avg_fps": round(avg_fps, 3), "p1_low_fps": round(p1_low_fps, 3), "frames": frames,
            "measured_s": round(measured_s, 3), "load_ms": round(load_ms, 3)}


def _write(path, result):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")


def main(argv=None):
    started = time.perf_counter()
    p = argparse.ArgumentParser(prog="chonoi.benchmark")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--duration", required=True, type=float)
    p.add_argument("--out", required=True)
    p.add_argument("--warmup", type=float, default=3.0)
    a = p.parse_args(argv)
    a.out = os.path.abspath(a.out)  # trước khi Pyxel có thể đổi thư mục làm việc
    if a.duration <= 0:
        p.error("--duration must be > 0")
    if a.warmup < 0:
        p.error("--warmup must be >= 0")
    try:
        import pyxel
        from play.main import Game
    except Exception as e:  # thiếu pyxel hoặc client không nạp được
        print(f"benchmark: cannot load Pyxel client: {e}", file=sys.stderr)
        return 1

    state = {"load_ms": None, "t0": None, "prev": None, "times": [], "done": False}

    def on_frame():
        now = time.perf_counter()
        if state["load_ms"] is None:
            state["load_ms"] = (now - started) * 1000
            state["t0"] = state["prev"] = now
            return
        dt, state["prev"] = now - state["prev"], now
        if now - state["t0"] < a.warmup:
            return
        state["times"].append(dt)
        if sum(state["times"]) >= a.duration:
            state["done"] = True
            _write(a.out, compute_metrics(state["times"], state["load_ms"]))
            pyxel.quit()

    try:
        Game(seed=a.seed, on_frame=on_frame, display_scale=WINDOW_SCALE)
    except Exception as e:
        print(f"benchmark: cannot open Pyxel window: {e}", file=sys.stderr)
        return 1
    if not state["done"]:
        print("benchmark: window closed before measurement finished", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
