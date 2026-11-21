"""Persistent top-10 leaderboard for the optional day extension."""

import json
import os
import tempfile

from .errors import BadInput

MAX_ENTRIES = 10


def _entry(value):
    if not isinstance(value, dict) or set(value) != {"name", "score", "days_completed", "seed"}:
        raise BadInput("leaderboard entry must contain name, score, days_completed, seed")
    if not isinstance(value["name"], str) or not value["name"].strip():
        raise BadInput("leaderboard.name must be a non-empty string")
    if isinstance(value["score"], bool) or not isinstance(value["score"], int):
        raise BadInput("leaderboard.score must be an integer")
    if isinstance(value["days_completed"], bool) or not isinstance(value["days_completed"], int) or value["days_completed"] < 0:
        raise BadInput("leaderboard.days_completed must be a non-negative integer")
    if isinstance(value["seed"], bool) or not isinstance(value["seed"], int):
        raise BadInput("leaderboard.seed must be an integer")
    return {"name": value["name"], "score": value["score"],
            "days_completed": value["days_completed"], "seed": value["seed"]}


def sort_entries(entries):
    # Python sort is stable: equal scores retain the earlier stored entry.
    return sorted(entries, key=lambda e: -e["score"])[:MAX_ENTRIES]


def read(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"cannot read leaderboard {path}: {e}")
    if not isinstance(data, dict) or set(data) != {"entries"} or not isinstance(data["entries"], list):
        raise BadInput("leaderboard store must be {\"entries\": [...]}")
    return sort_entries([_entry(e) for e in data["entries"]])


def write(path, entries):
    entries = sort_entries([_entry(e) for e in entries])
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".leaderboard-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"entries": entries}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def record(path, entry):
    entries = read(path)
    entries.append(_entry(entry))
    write(path, entries)


def export(path, out_path):
    entries = read(path)
    directory = os.path.dirname(os.path.abspath(out_path))
    fd, tmp = tempfile.mkstemp(prefix=".leaderboard-export-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"entries": entries}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, out_path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
