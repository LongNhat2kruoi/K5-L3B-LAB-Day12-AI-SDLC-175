"""Buổi tối — Mở Quán. KHUNG: đi lại, chặn biên, đồng hồ, kho nạp từ file/scenario.

Nhóm viết tiếp (PRD-0 mục F, Quán):
  TODO(nhóm, lát 3): khách đến theo lịch, chọn món nấu được, giữ chỗ nguyên liệu, kiên nhẫn,
                     bỏ đi (customer_left), no_dish, vòng đời khách.
  TODO(nhóm, lát 4): interact tại bếp/bàn (cook_started, dish_ready, dish_picked, served),
                     ăn xong trả tiền (paid), boa, uy tín, hết ca (quan_end).
"""

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from .ramp import ramp_velocity

TICK = 60.0


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None):
        t = tuning["quan"]
        self.t = t
        self.menu = tuning["menu"]
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = list(p.get("pos", t["start_pos"]))
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # kho: --inventory HOẶC scenario.stock (cả hai -> cli đã báo mã 2)
        self.stock = dict(inventory if inventory is not None else scenario.get("stock", {}))
        self.hand = scenario.get("hand")
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * 60)))
        self.reputation = scenario.get("reputation", t["reputation_initial"])
        self.stoves = [dict(s, state=s.get("state", "idle"), dish=s.get("dish"),
                            cook_ticks_left=s.get("cook_ticks_left", 0), ready_ticks=s.get("ready_ticks", 0))
                       for s in self._merge(t["stoves"], scenario.get("stoves", []))]
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        self.customers = self._build_customers(scenario.get("customers", []))
        for e in self.customers:
            ids.reserve(e["id"])
        self._check_fixture()
        self.money = 0
        self.earned = 0
        self.shift_earned = 0
        self.done = False
        self.reason = None

    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    def _build_customers(self, raw):
        patience_max = int(round(self.t["patience_s"] * 60))
        out = []
        for c in raw:
            e = {"id": c["id"], "table_id": c["table_id"], "dish_id": c["dish_id"],
                 "order_tick": c.get("order_tick", 0), "state": c.get("state", "waiting"),
                 "patience_ticks_left": c.get("patience_ticks_left", patience_max),
                 "eat_ticks_left": c.get("eat_ticks_left", 0),
                 "order_status": c.get("order_status", "reserved"),
                 "base_price": c.get("base_price"), "tip": c.get("tip")}
            if "reserved" in c:
                e["reserved"] = {k: v for k, v in sorted(c["reserved"].items()) if v > 0}
            out.append(e)
        # đơn reserved thiếu reserved: cấp theo công thức, xét (order_tick, id bàn)
        for e in sorted(out, key=lambda x: (x["order_tick"], id_key(x["table_id"]))):
            if "reserved" not in e:
                recipe = dict(sorted(self.menu[e["dish_id"]]["recipe"].items()))
                e["reserved"] = recipe if e["order_status"] == "reserved" else {}
        return out

    def _check_fixture(self):
        held = {}
        for c in self.customers:
            if c["order_status"] == "reserved":
                if c["reserved"] != self.menu[c["dish_id"]]["recipe"]:
                    raise BadInput(f"customers.{c['id']}: reserved khác công thức món")
                for k, v in c["reserved"].items():
                    held[k] = held.get(k, 0) + v
            elif c["reserved"]:
                raise BadInput(f"customers.{c['id']}: đơn không phải reserved thì reserved phải rỗng")
            eating = c["state"] == "eating"
            if eating != (c["order_status"] == "served"):
                raise BadInput(f"customers.{c['id']}: state eating khi và chỉ khi order_status served")
            if eating:
                if c["eat_ticks_left"] <= 0 or not isinstance(c["base_price"], int) or not isinstance(c["tip"], int):
                    raise BadInput(f"customers.{c['id']}: khách eating cần eat_ticks_left > 0 và base_price, tip nguyên")
            elif c["eat_ticks_left"] != 0:
                raise BadInput(f"customers.{c['id']}: khách waiting cần eat_ticks_left = 0")
        for k, v in held.items():
            if v > self.stock.get(k, 0):
                raise BadInput(f"giữ chỗ {k} quá tồn: {v} > {self.stock.get(k, 0)}")
        for s in self.stoves:
            st, d = s["state"], s["dish"]
            ok = {"idle": d is None and s["cook_ticks_left"] == 0 and s["ready_ticks"] == 0,
                  "cooking": d is not None and s["cook_ticks_left"] > 0,
                  "ready": d is not None and s["cook_ticks_left"] == 0}[st]
            if not ok:
                raise BadInput(f"bếp {s['id']}: trạng thái {st} mâu thuẫn với dish/timer")
        holders = [(f"bếp {s['id']}", s["dish"]) for s in self.stoves if s["dish"] is not None]
        if self.hand is not None:
            holders.append(("tay", self.hand))
        by_id = {c["id"]: c for c in self.customers}
        seen = set()
        for where, d in holders:
            c = by_id.get(d["order_id"])
            if c is None:
                raise BadInput(f"{where}: liên kết thiếu, không có khách {d['order_id']}")
            if c["order_status"] != "assigned":
                raise BadInput(f"{where}: đơn {c['id']} không ở trạng thái assigned")
            if d["dish_id"] != c["dish_id"]:
                raise BadInput(f"{where}: dish_id khác món của khách {c['id']}")
            if c["id"] in seen:
                raise BadInput(f"đơn {c['id']} được giữ ở hai nơi")
            seen.add(c["id"])
        for c in self.customers:
            if c["order_status"] == "assigned" and c["id"] not in seen:
                raise BadInput(f"customers.{c['id']}: đơn assigned phải có đúng một món")

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": self.pos, "vel": self.vel},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks")}
                       for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": sort_by_id(self.customers),
        }

    def step(self, inp):
        events = []
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        # TODO(nhóm): giảm kiên nhẫn / nấu / ăn; bếp chín -> ready; xử lý khách theo thứ tự PRD-0 mục F.
        self._move(inp)
        # TODO(nhóm): tối đa MỘT interact, chọn đối tượng theo (khoảng cách, bếp trước bàn, id).
        # TODO(nhóm): khách mới theo lịch (first_customer_tick, customer_interval_s), no_dish.
        if self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                        "shift_earned": self.shift_earned, "reputation": self.reputation}))
        return events

    def _move(self, inp):
        speed = self.t["walk_speed"]
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t.get("ramp_max_ticks", 6)))
        b = self.t["bounds"]
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])
