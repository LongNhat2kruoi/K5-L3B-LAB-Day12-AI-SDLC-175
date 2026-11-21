"""Buổi tối — Mở Quán. KHUNG: đi lại, chặn biên, đồng hồ, kho nạp từ file/scenario.

Luật khách đến, bếp, phục vụ, trả tiền và hết ca: PRD-0 mục F (Quán).
"""

import math
from fractions import Fraction

from .. import fresh
from ..errors import BadInput
from ..ids import id_key, sort_by_id
from ..inventory import validate_item_list
from .ramp import ramp_velocity

TICK = 60.0


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None, plan_dishes=None):
        t = tuning["quan"]
        self.t = t
        self.menu = tuning["menu"]
        self.rng = streams
        # kế hoạch món của ngày (mode day truyền vào); None = cả menu
        self.plan_dishes = None if plan_dishes is None else frozenset(plan_dishes)
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = list(p.get("pos", t["start_pos"]))
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # Mô hình chung: stock là list cá thể {"id","kind","fresh": Fraction} cho cả v1.1 lẫn v1.2.
        # v1.1 (cờ tắt): kho đếm -> cá thể id tạm, fresh 100, không hao; chỉ I/O và hao/ươn/giá khác theo cờ.
        self.v12 = fresh.enabled(tuning)
        self.compat_legacy = inventory is None and bool(t.get("_legacy_compat"))
        if self.v12:
            self.decay = fresh.per_tick(tuning, "quan")
            self.threshold = fresh.threshold(tuning)
        # kho: --inventory HOẶC scenario.stock (cả hai -> cli đã báo mã 2)
        self.items = self._build_stock(inventory if inventory is not None else scenario.get("stock", [] if self.v12 else {}))
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
        self._resolve_reservations()
        self.phase_tick = 0
        self.random_customers = scenario.get("random_customers", True)
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

    @property
    def stock(self):
        """v1.2: list cá thể; v1.1: object đếm theo loại (giữ nguyên hình dạng cũ)."""
        if self.v12:
            return self.items
        counts = {}
        for it in self.items:
            counts[it["kind"]] = counts.get(it["kind"], 0) + 1
        return {k: counts[k] for k in sorted(counts)}

    def _set_held(self, c, ids):
        """Phần giữ chỗ: `held` là list id (nội bộ); `reserved` là dạng xuất của phiên bản."""
        c["held"] = sorted(ids, key=id_key)
        if self.v12:
            c["reserved"] = list(c["held"])
        else:
            kind = {it["id"]: it["kind"] for it in self.items}
            counts = {}
            for i in c["held"]:
                counts[kind[i]] = counts.get(kind[i], 0) + 1
            c["reserved"] = {k: counts[k] for k in sorted(counts)}

    def _build_stock(self, raw):
        if self.v12:
            if not isinstance(raw, list):
                if not (self.compat_legacy and isinstance(raw, dict)):
                    raise BadInput("contract v1.2: kho quán phải là mảng cá thể, không nhận kho đếm")
                out, n = [], 0
                for k in sorted(raw):
                    for _ in range(max(0, raw[k])):
                        n += 1
                        out.append({"id": f"_S{n}", "kind": k, "fresh": 100})
                return out
            # file kho đã chuẩn hóa (fresh là Fraction) đi thẳng; scenario.stock còn là số JSON thô
            exact = {i: e["fresh"] for i, e in enumerate(raw) if isinstance(e, dict) and isinstance(e.get("fresh"), Fraction)}
            plain = [dict(e, fresh=0) if i in exact else e for i, e in enumerate(raw)]
            out = validate_item_list(plain)
            for i, f in exact.items():
                if not (0 <= f <= 100):
                    raise BadInput(f"fresh phải trong [0, 100], đang là {f}")
                out[i]["fresh"] = f
            return out
        if not isinstance(raw, dict):
            raise BadInput("contract v1.1: kho quán phải là object đếm, không nhận mảng cá thể")
        out, n = [], 0
        for k in sorted(raw):
            for _ in range(max(0, raw[k])):
                n += 1
                out.append({"id": f"_S{n}", "kind": k, "fresh": Fraction(100)})
        return out

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
                r = c["reserved"]
                if self.v12:
                    if not isinstance(r, list):
                        if self.compat_legacy and isinstance(r, dict):
                            # Legacy fixtures describe kinds; v1.3 runtime allocates exact ids later.
                            pass
                        else:
                            raise BadInput(f"customers.{c['id']}: contract v1.2 cần reserved là mảng id cá thể")
                    else:
                        e["reserved"] = list(r)
                else:
                    if not isinstance(r, dict):
                        raise BadInput(f"customers.{c['id']}: contract v1.1 cần reserved là object kind -> số")
                    e["reserved"] = {k: v for k, v in sorted(r.items()) if v > 0}
            out.append(e)
        return out

    def _resolve_reservations(self):
        """Chuẩn hóa reserved về list id cá thể; kiểm giữ chỗ và cấp phần giữ còn thiếu."""
        ordered = sorted(self.customers, key=lambda x: (x["order_tick"], id_key(x["table_id"])))
        if self.v12:
            self._resolve_v12(ordered)
        else:
            self._resolve_v11(ordered)

    def _resolve_v11(self, ordered):
        # đơn reserved thiếu reserved: cấp theo công thức, xét (order_tick, id bàn)
        for e in ordered:
            if "reserved" not in e:
                recipe = dict(sorted(self.menu[e["dish_id"]]["recipe"].items()))  # bản sao, không dùng chung với menu
                e["reserved"] = recipe if e["order_status"] == "reserved" else {}
        self._check_fixture()
        held = {}
        for e in ordered:
            for k, v in e["reserved"].items():
                held[k] = held.get(k, 0) + v
        for k, v in held.items():
            have = sum(1 for it in self.items if it["kind"] == k)
            if v > have:
                raise BadInput(f"giữ chỗ {k} quá tồn: {v} > {have}")
        taken = set()
        for e in ordered:  # đổi map kind -> số thành id cá thể (tươi nhất rồi id nhỏ)
            ids = []
            for k, n in e["reserved"].items():
                ids.extend(self._pick(k, n, taken | set(ids)))
            taken.update(ids)
            self._set_held(e, ids)

    def _resolve_v12(self, ordered):
        by_id = {it["id"]: it for it in self.items}
        taken = set()
        for e in ordered:
            if "reserved" not in e:
                continue
            if e["order_status"] != "reserved":
                if e["reserved"]:
                    raise BadInput(f"customers.{e['id']}: đơn không phải reserved thì reserved phải rỗng")
                continue
            kinds = {}
            for i in e["reserved"]:
                it = by_id.get(i)
                if it is None:
                    raise BadInput(f"customers.{e['id']}: reserved trỏ id không có trong kho: {i}")
                if it["fresh"] < self.threshold:
                    raise BadInput(f"customers.{e['id']}: reserved trỏ cá thể ươn: {i}")
                if i in taken:
                    raise BadInput(f"customers.{e['id']}: cá thể {i} đã được đơn khác giữ")
                taken.add(i)
                kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
            if kinds != self.menu[e["dish_id"]]["recipe"]:
                raise BadInput(f"customers.{e['id']}: reserved khác công thức món")
            e["reserved"] = sorted(e["reserved"], key=id_key)
        for e in ordered:
            if "reserved" in e:
                continue
            if e["order_status"] != "reserved":
                e["reserved"] = []
                continue
            got = self._try_hold(self.menu[e["dish_id"]]["recipe"], taken)
            if got is None:
                raise BadInput(f"customers.{e['id']}: kho không đủ cá thể tươi để giữ cho món")
            taken.update(got)
            e["reserved"] = got
        self._check_fixture()
        for e in ordered:
            self._set_held(e, e["reserved"])

    def _usable(self, it):
        return not self.v12 or it["fresh"] >= self.threshold

    def _pick(self, kind, n, taken):
        """n cá thể `kind` dùng được, chưa nằm trong `taken`: tươi nhất rồi id nhỏ; thiếu -> ít hơn n."""
        pool = [it for it in self.items if it["kind"] == kind and it["id"] not in taken and self._usable(it)]
        pool.sort(key=lambda it: (-it["fresh"], id_key(it["id"])))
        return [it["id"] for it in pool[:n]]

    def _try_hold(self, recipe, taken):
        """Giữ đủ công thức từ cá thể khả dụng (chưa ươn, chưa giữ); không đủ -> None."""
        out = []
        for k, n in sorted(recipe.items()):
            got = self._pick(k, n, taken | set(out))
            if len(got) < n:
                return None
            out.extend(got)
        return sorted(out, key=id_key)

    def _held_ids(self):
        return {i for c in self.customers for i in c["held"]}

    def _check_fixture(self):
        for c in self.customers:
            if self.plan_dishes is not None and c["dish_id"] not in self.plan_dishes:
                raise BadInput(f"customers.{c['id']}: món {c['dish_id']} ngoài kế hoạch")
            if c["order_status"] == "reserved":
                if not self.v12 and c["reserved"] != self.menu[c["dish_id"]]["recipe"]:
                    raise BadInput(f"customers.{c['id']}: reserved khác công thức món")
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
        for s in self.stoves:
            st, d = s["state"], s["dish"]
            ok = {"idle": d is None and s["cook_ticks_left"] == 0 and s["ready_ticks"] == 0,
                  "cooking": d is not None and s["cook_ticks_left"] > 0 and s["ready_ticks"] == 0,
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
            "stock": self._stock_json(),
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks")}
                       for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": [{k: v for k, v in c.items() if k != "held"} for c in sort_by_id(self.customers)],
        }

    def _stock_json(self):
        if self.v12:
            return [{"id": it["id"], "kind": it["kind"], "fresh": fresh.to_json(it["fresh"])}
                    for it in sort_by_id(self.items)]
        return self.stock

    def step(self, inp):
        events = []
        # Bước 1: đồng hồ, kiên nhẫn (khách waiting), timer ăn (khách eating)
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        for c in self.customers:
            if c["state"] == "waiting":
                c["patience_ticks_left"] = max(0, c["patience_ticks_left"] - 1)
            elif c["state"] == "eating":
                c["eat_ticks_left"] = max(0, c["eat_ticks_left"] - 1)
        for s in self.stoves:
            if s["state"] == "cooking":
                s["cook_ticks_left"] = max(0, s["cook_ticks_left"] - 1)
            elif s["state"] == "ready":
                s["ready_ticks"] += 1
        # Bước 1b (v1.2): hao tươi kho thô, phát hết spoiled theo id, rồi mới xử lý giữ chỗ bị ươn
        if self.v12:
            self._decay_stock(events)
        # Bước 2: bếp chín -> ready, rồi di chuyển
        for s in self.stoves:
            if s["state"] == "cooking" and s["cook_ticks_left"] == 0:
                s.update(state="ready", ready_ticks=0)
                events.append(("dish_ready", {"stove_id": s["id"], "order_id": s["dish"]["order_id"],
                                              "dish_id": s["dish"]["dish_id"]}))
        self._move(inp)
        # Bước 3: tối đa MỘT interact, chỉ với đối tượng gần nhất (R11)
        if inp.pressed("interact"):
            self._interact(events)
        # Bước 4: khách rời / trả tiền theo id bàn
        in_time = self.time_left_ticks > 0
        for c in sort_by_id(self.customers, key=lambda x: x["table_id"]):
            if c["state"] == "eating":
                if c["eat_ticks_left"] == 0:
                    self._pay(events, c, "finished_eating")
                elif not in_time:
                    self._pay(events, c, "closing")
                continue
            if c["state"] != "waiting":
                continue
            if in_time:
                if c["patience_ticks_left"] == 0:
                    self._add_reputation(self.t["left_reputation_delta"])
                    self._leave(events, c, "patience")
            else:
                self._leave(events, c, "closing")
        if not in_time:
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                        "shift_earned": self.shift_earned, "reputation": self.reputation}))
            return events
        # Bước 5: khách mới theo lịch
        if self.random_customers and self._customer_due():
            self._spawn_customer(events)
        return events

    def _decay_stock(self, events):
        spoiled = []
        for it in self.items:
            was = it["fresh"]
            it["fresh"] = max(Fraction(0), was - self.decay)
            if was >= self.threshold > it["fresh"]:
                spoiled.append(it)
        spoiled = sort_by_id(spoiled)
        for it in spoiled:
            events.append(("spoiled", {"item_id": it["id"], "kind": it["kind"], "location": "stock"}))
        gone = {it["id"] for it in spoiled}
        if not gone:
            return
        affected = [c for c in self.customers if c["order_status"] == "reserved" and gone.intersection(c["held"])]
        for c in sorted(affected, key=lambda x: (x["order_tick"], id_key(x["table_id"]))):
            self._set_held(c, [])  # nhả toàn bộ phần giữ, thử giữ lại đúng một lần
            got = self._try_hold(self.menu[c["dish_id"]]["recipe"], self._held_ids())
            if got is None:
                c["order_status"] = "unfulfillable"
            else:
                self._set_held(c, got)

    def _add_reputation(self, delta):
        lo, hi = self.t["reputation_min"], self.t["reputation_max"]
        self.reputation = min(hi, max(lo, self.reputation + delta))

    def _interact(self, events):
        r = self.t["interact_radius"]
        cands = []
        for kind, objs in ((0, self.stoves), (1, self.tables)):
            for o in objs:
                d = math.hypot(o["pos"][0] - self.pos[0], o["pos"][1] - self.pos[1])
                if d <= r:
                    cands.append((d, kind, id_key(o["id"]), o))
        if not cands:
            return
        _, kind, _, o = min(cands, key=lambda x: x[:3])
        if kind == 0:
            self._use_stove(events, o)
        else:
            self._use_table(events, o)

    def _use_stove(self, events, s):
        if s["state"] == "idle":
            orders = [c for c in self.customers if c["order_status"] == "reserved"]
            if not orders:
                return
            c = min(orders, key=lambda x: (x["order_tick"], id_key(x["table_id"])))
            menu = self.menu[c["dish_id"]]
            held = set(c["held"])
            used = [it for it in self.items if it["id"] in held]
            used.sort(key=lambda it: (it["kind"], id_key(it["id"])))
            if self.v12:
                items = [{"id": it["id"], "kind": it["kind"], "fresh": fresh.to_json(it["fresh"])} for it in used]
                price = math.floor(menu["price"] * (sum(it["fresh"] for it in used) / len(used)) / 100)
            else:
                items = [it["kind"] for it in used]
                price = menu["price"]
            self.items = [it for it in self.items if it["id"] not in held]
            self._set_held(c, [])
            c["order_status"] = "assigned"
            c["base_price"] = price
            s.update(state="cooking", cook_ticks_left=int(round(menu["cook_s"] * 60)),
                     dish={"order_id": c["id"], "dish_id": c["dish_id"], "base_price": price})
            events.append(("cook_started", {"stove_id": s["id"], "order_id": c["id"], "dish_id": c["dish_id"],
                                            "items": items, "base_price": price}))
        elif s["state"] == "ready" and self.hand is None:
            d = s["dish"]
            self.hand = d
            s.update(state="idle", dish=None, cook_ticks_left=0, ready_ticks=0)
            events.append(("dish_picked", {"stove_id": s["id"], "order_id": d["order_id"], "dish_id": d["dish_id"]}))

    def _use_table(self, events, tb):
        if self.hand is None:
            return
        c = next((x for x in self.customers if x["table_id"] == tb["id"]), None)
        if c is None or c["id"] != self.hand["order_id"] or c["state"] != "waiting":
            return
        patience_max = int(round(self.t["patience_s"] * 60))
        base = self.hand["base_price"]
        tip = 0
        if c["patience_ticks_left"] / patience_max >= self.t["tip_min_patience_ratio"]:
            tip = math.floor(base * self.t["tip_rate"])
        c.update(state="eating", order_status="served", base_price=base, tip=tip,
                 eat_ticks_left=int(round(self.t["eat_s"] * 60)))
        self.hand = None
        events.append(("served", {"order_id": c["id"], "table_id": c["table_id"], "dish_id": c["dish_id"],
                                  "patience_ticks_left": c["patience_ticks_left"], "base_price": base, "tip": tip}))

    def _pay(self, events, c, reason):
        amount = c["base_price"] + c["tip"]
        self.money += amount
        self.earned += amount
        self.shift_earned += amount
        if c["tip"] > 0:
            self._add_reputation(self.t["tip_reputation"])
        self._remove_customer(c)
        events.append(("paid", {"order_id": c["id"], "table_id": c["table_id"], "base_price": c["base_price"],
                                "tip": c["tip"], "amount": amount, "reason": reason}))

    def _leave(self, events, c, reason):
        self._remove_customer(c)
        events.append(("customer_left", {"order_id": c["id"], "table_id": c["table_id"],
                                         "reason": reason, "reputation": self.reputation}))

    def _customer_due(self):
        first = self.t["first_customer_tick"]
        interval = int(round(self.t["customer_interval_s"] * 60))
        return self.phase_tick >= first and (self.phase_tick - first) % interval == 0

    def _available(self):
        """Số cá thể dùng được (chưa ươn) và chưa bị giữ, theo loại."""
        held = self._held_ids()
        avail = {}
        for it in self.items:
            n = 1 if it["id"] not in held and self._usable(it) else 0
            avail[it["kind"]] = avail.get(it["kind"], 0) + n
        return avail

    def _spawn_customer(self, events):
        taken = {c["table_id"] for c in self.customers}
        free = [tb for tb in self.tables if tb["id"] not in taken]
        if not free:
            return
        table = free[0]  # self.tables đã sắp theo id
        avail = self._available()
        cands = [d for d in sorted(self.menu)
                 if (self.plan_dishes is None or d in self.plan_dishes)
                 and all(avail.get(k, 0) >= n for k, n in self.menu[d]["recipe"].items())]
        if not cands:
            events.append(("no_dish", {}))
            return
        dish = cands[self.rng.get("customer_dish").randrange(len(cands))]
        c = {"id": self.ids.new("C"), "table_id": table["id"], "dish_id": dish,
             "order_tick": self.phase_tick, "state": "waiting",
             "patience_ticks_left": int(round(self.t["patience_s"] * 60)), "eat_ticks_left": 0,
             "order_status": "reserved", "reserved": None,
             "base_price": None, "tip": None}
        self._set_held(c, self._try_hold(self.menu[dish]["recipe"], self._held_ids()))
        self.customers.append(c)
        events.append(("customer_arrived", {"order_id": c["id"], "table_id": c["table_id"], "dish_id": dish}))

    def _remove_customer(self, c):
        """Khách rời: nhả giữ chỗ, bỏ món của đơn trên bếp / tay."""
        self.customers.remove(c)
        for s in self.stoves:
            if s["dish"] is not None and s["dish"]["order_id"] == c["id"]:
                s.update(state="idle", dish=None, cook_ticks_left=0, ready_ticks=0)
        if self.hand is not None and self.hand["order_id"] == c["id"]:
            self.hand = None

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
