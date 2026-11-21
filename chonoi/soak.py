"""Ten-day deterministic day-mode soak command for Contract v1.3."""

import argparse
import json
import time

from .contract import load_contract
from .inputs import InputPlayer
from .runner import Session
from .scenario import load_scenario


def _run_day(tuning, seed):
    scenario = load_scenario(None, "day", tuning)
    session = Session("day", tuning, scenario, seed)
    player = InputPlayer([])
    limit = int((tuning["gather"]["duration_s"] + tuning["quan"]["duration_s"]) * tuning["tick_hz"] + 2)
    for _ in range(limit):
        if session.done:
            break
        session.step(player.advance(session.tick))
    if not session.done:
        raise RuntimeError("day did not complete before its deterministic limit")
    return session.end_row()


def main(argv=None):
    p = argparse.ArgumentParser(prog="chonoi.soak")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--days", required=True, type=int)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    if a.days <= 0:
        p.error("--days must be > 0")
    started = time.perf_counter()
    contract = load_contract()
    tuning = contract["tuning"]
    results = []
    crashes = 0
    for day in range(1, a.days + 1):
        try:
            end = _run_day(tuning, a.seed + day - 1)
            results.append({"day": day, "earned": end["earned"],
                            "reputation": end["reputation"], "score": end["score"]})
        except Exception:
            crashes += 1
            break
    out = {"days": a.days, "days_completed": len(results), "crashes": crashes,
           "results": results, "duration_s": round(time.perf_counter() - started, 3)}
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    return 0 if crashes == 0 and len(results) == a.days else 1


if __name__ == "__main__":
    raise SystemExit(main())
