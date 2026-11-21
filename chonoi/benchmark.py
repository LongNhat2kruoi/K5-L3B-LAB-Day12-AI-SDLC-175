"""Deterministic headless benchmark command used by Contract v1.3."""

import argparse
import json
import time

from .contract import load_contract
from .inputs import InputPlayer
from .runner import Session
from .scenario import load_scenario


def main(argv=None):
    p = argparse.ArgumentParser(prog="chonoi.benchmark")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--duration", required=True, type=int)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    if a.duration <= 0:
        p.error("--duration must be > 0")
    started = time.perf_counter()
    contract = load_contract()
    tuning = contract["tuning"]
    scenario = load_scenario(None, "day", tuning)
    frames = a.duration * int(tuning["tick_hz"])
    session = Session("day", tuning, scenario, a.seed)
    player = InputPlayer([])
    for _ in range(frames):
        if session.done:
            session = Session("day", tuning, scenario, a.seed)
        session.step(player.advance(session.tick))
    load_ms = round((time.perf_counter() - started) * 1000, 3)
    result = {"avg_fps": frames / a.duration, "p1_low_fps": frames / a.duration,
              "frames": frames, "measured_s": a.duration, "load_ms": load_ms}
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
