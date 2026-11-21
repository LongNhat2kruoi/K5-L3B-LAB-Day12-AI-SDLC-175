"""File kho v1.0 (Contract G): {"items": {id: số nguyên >= 0}}.

Đọc: từ chối sai schema / id lạ / số âm (BadInput -> mã 2).
Ghi: bỏ mục bằng 0, qua file tạm cùng thư mục rồi thay thế, byte-ổn-định.
"""

import json
import os
import tempfile

from . import fresh
from .errors import BadInput
from .ids import id_key

KINDS = ("ca_loc", "ca_linh", "bong_dien_dien", "bong_sung", "ca_keo", "keo_neo")
KINDS_P1 = KINDS  # bí danh cho code cũ


def validate_items(items, kinds=KINDS):
    if not isinstance(items, dict):
        raise BadInput("items phải là object")
    out = {}
    for k, v in items.items():
        if k not in kinds:
            raise BadInput(f"nguyên liệu lạ: {k}")
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise BadInput(f"số lượng không hợp lệ cho {k}: {v!r}")
        if v > 0:
            out[k] = v
    return out


def validate_item_list(items, kinds=KINDS) -> list:
    """Kho cá thể v1.2: mảng {id, kind, fresh}; trả bản chuẩn hóa (fresh là Fraction), giữ thứ tự."""
    if not isinstance(items, list):
        raise BadInput("items phải là mảng cá thể")
    out, seen = [], set()
    for e in items:
        if not isinstance(e, dict) or set(e) != {"id", "kind", "fresh"}:
            raise BadInput("mỗi cá thể phải là object đúng 3 khóa id, kind, fresh")
        i, k = e["id"], e["kind"]
        if not isinstance(i, str) or not i:
            raise BadInput(f"id cá thể phải là chuỗi khác rỗng: {i!r}")
        if i in seen:
            raise BadInput(f"id cá thể trùng: {i}")
        seen.add(i)
        if not isinstance(k, str) or k not in kinds:
            raise BadInput(f"nguyên liệu lạ: {k!r}")
        out.append({"id": i, "kind": k, "fresh": fresh.parse(e["fresh"])})
    return out


def read_inventory(path: str, kinds=KINDS):
    """Trả dict đếm (items là object) hoặc list cá thể (items là mảng); bên dùng chọn theo contract."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    if isinstance(data["items"], list):
        return validate_item_list(data["items"], kinds)
    return validate_items(data["items"], kinds)


def hold_to_items(hold: list) -> dict:
    """Khoang (mảng id theo thứ tự nhặt) -> object đếm, sắp theo id nguyên liệu."""
    counts = {}
    for k in hold:
        counts[k] = counts.get(k, 0) + 1
    return {k: counts[k] for k in sorted(counts)}


def write_inventory(path: str, items):
    if isinstance(items, list):
        items = [{"id": e["id"], "kind": e["kind"], "fresh": fresh.to_json(e["fresh"])}
                 for e in sorted(items, key=lambda e: id_key(e["id"]))]
    else:
        items = {k: items[k] for k in sorted(items) if items[k] > 0}
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"items": items}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
