"""Điểm vào headless: python3 -m chonoi.headless --mode day --seed 1 --ticks 600 --out out.jsonl

Mã thoát: 0 bình thường; 2 tham số/đầu vào sai (kiểm TRƯỚC khi ghi đầu ra); 1 lỗi chạy/ghi.
"""

import argparse
import json
import os
import sys

from .contract import load_contract
from .errors import BadInput
from .inputs import load_frames
from .inventory import read_inventory
from .leaderboard import export as export_leaderboard, record as record_leaderboard
from .runner import run
from .scenario import load_scenario


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


def _int(name):
    def conv(s):
        try:
            return int(s)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{name} phải là số nguyên")
    return conv


def main(argv=None) -> int:
    p = _Parser(prog="chonoi.headless")
    p.add_argument("--mode", choices=["gather", "quan", "day"])
    p.add_argument("--seed", type=_int("seed"))
    p.add_argument("--ticks", type=_int("ticks"))
    p.add_argument("--out")
    p.add_argument("--days", type=_int("days"), default=1)
    p.add_argument("--leaderboard")
    p.add_argument("--player-name")
    p.add_argument("--export-leaderboard")
    p.add_argument("--scenario")
    p.add_argument("--inputs")
    p.add_argument("--inventory")
    p.add_argument("--inventory-out", dest="inventory_out")
    p.add_argument("--snapshot-every", dest="snapshot_every", type=_int("snapshot-every"), default=10)
    a = p.parse_args(argv)
    if a.export_leaderboard:
        try:
            export_leaderboard(a.leaderboard or "leaderboard.json", a.export_leaderboard)
        except (BadInput, OSError) as e:
            sys.stderr.write(f"đầu vào sai: {e}\n")
            return 2
        return 0
    if a.mode is None or a.seed is None or a.ticks is None or a.out is None:
        p.error("normal mode requires --mode, --seed, --ticks and --out")
    try:
        if a.ticks < 0:
            raise BadInput("--ticks phải >= 0")
        if a.snapshot_every <= 0:
            raise BadInput("--snapshot-every phải > 0")
        if a.days <= 0:
            raise BadInput("--days phải > 0")
        if (a.player_name is None) != (a.leaderboard is None):
            raise BadInput("--leaderboard và --player-name phải đi cùng nhau")
        if a.player_name is not None and a.mode != "day":
            raise BadInput("--player-name chỉ dùng với --mode day")
        if a.player_name is not None and a.days != 5:
            raise BadInput("leaderboard chỉ ghi lượt chuẩn đủ 5 ngày")
        if a.player_name is not None and a.scenario:
            raise BadInput("leaderboard không nhận scenario")
        if a.inventory and a.mode != "quan":
            raise BadInput("--inventory chỉ dùng với quan")
        if a.inventory_out and a.mode != "gather":
            raise BadInput("--inventory-out chỉ dùng với gather")
        outs = [x for x in (a.out, a.inventory_out) if x]
        ins = [x for x in (a.scenario, a.inputs, a.inventory) if x]
        paths = [os.path.abspath(x) for x in outs + ins]
        if len(set(paths)) != len(paths):
            raise BadInput("các đường dẫn đầu vào/đầu ra phải khác nhau")
        contract = load_contract()
        leaderboard_path = a.leaderboard or contract.get("extensions", {}).get("leaderboard", {}).get("store", "leaderboard.json")
        tuning = contract["tuning"]
        scenario = load_scenario(a.scenario, a.mode, tuning)
        frames = load_frames(a.inputs)
        inventory = read_inventory(a.inventory) if a.inventory else None
        if inventory is not None and "stock" in scenario:
            raise BadInput("vừa có quan.stock vừa có --inventory")
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    try:
        if a.player_name is not None:
            # Mỗi ngày chuẩn là một session độc lập với cùng contract; file out giữ ca cuối.
            total_score = 0
            for day in range(a.days):
                run(a.mode, tuning, scenario, a.seed + day, frames, a.ticks, a.out, a.snapshot_every,
                    inventory=inventory, inventory_out=a.inventory_out)
                with open(a.out, encoding="utf-8") as f:
                    end = json.loads(f.readlines()[-1])
                total_score += int(end.get("score", 0))
            record_leaderboard(leaderboard_path, {"name": a.player_name, "score": total_score,
                                               "days_completed": a.days, "seed": a.seed})
        else:
            run(a.mode, tuning, scenario, a.seed, frames, a.ticks, a.out, a.snapshot_every,
                inventory=inventory, inventory_out=a.inventory_out)
    except BadInput as e:  # lỗi mức luật phát hiện lúc dựng sim
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"lỗi ghi: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
