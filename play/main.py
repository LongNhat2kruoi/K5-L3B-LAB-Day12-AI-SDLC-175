"""Quán Ăn Chợ Nổi: bản chơi Pyxel (320x180, phóng x4 = 1280x720). Chạy CÙNG lớp luật với headless qua chonoi.runner.Session.

Web:  python -m http.server 8000   rồi mở http://localhost:8000/play/
Máy:  python play/main.py          (cần `pip install pyxel`; Windows bật Smart App Control sẽ chặn, dùng bản web)

Vòng ngày: Menu → DayIntro → sáng (gather) → EveningIntro → tối (quan) → DayResult → Shop → Ngày kế (5 Ngày) → Summary.
Giao diện chỉ ĐỌC snapshot/sự kiện; trường nào luật chưa có thì bỏ qua. Không có gì ở đây ảnh hưởng headless.
Phím: WASD/mũi tên · E tương tác · Space bắt cá · Enter tiếp tục · Esc/P tạm dừng · H hướng dẫn.
"""
import copy
import json
import math
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pyxel  # noqa: E402

from chonoi.contract import load_contract  # noqa: E402
from chonoi.inputs import LiveInputs  # noqa: E402
from chonoi.runner import Session  # noqa: E402

ASSETS = os.path.join(ROOT, "play", "assets")
W, H = 320, 180
SEED = 1
DAYS = 5
(INK, HAIR, MUD, SILT, DAWN, CREAM, IND_DK, IND, GLASS, SKIN, SKIN_DK,
 WOOD_DK, BAMBOO, PALM, LANTERN, RED) = range(16)
KEY = LANTERN

KIND = {"ca_linh": ("cá linh", GLASS), "ca_loc": ("cá lóc", MUD), "ca_keo": ("cá kèo", SKIN_DK),
        "bong_dien_dien": ("điên điển", LANTERN), "bong_sung": ("bông súng", RED), "keo_neo": ("kèo nèo", PALM)}
DISH = {"ca_loc_nuong_trui": "Cá lóc nướng trui", "goi_bong_sung": "Gỏi bông súng",
        "lau_ca_linh_dien_dien": "Lẩu cá linh điên điển", "canh_chua_ca_loc": "Canh chua cá lóc",
        "ca_keo_nuong": "Cá kèo nướng muối ớt", "lau_mam": "Lẩu mắm miền Tây"}
SHORT = {"ca_loc_nuong_trui": "cá lóc nướng", "goi_bong_sung": "gỏi bông súng",
         "lau_ca_linh_dien_dien": "lẩu cá linh", "canh_chua_ca_loc": "canh chua",
         "ca_keo_nuong": "cá kèo nướng", "lau_mam": "lẩu mắm"}  # tên gọn cho HUD / gợi ý

# shortcut: số của TICKET-02 cho tới khi game.contract.json lên v1.1 (day_plan, shop, 6 món); có khóa thì đọc khóa.
TICKET_MENU = {"canh_chua_ca_loc": {"ca_loc": 1, "bong_dien_dien": 1},
               "ca_keo_nuong": {"ca_keo": 2},
               "lau_mam": {"ca_linh": 2, "ca_keo": 1, "keo_neo": 1, "bong_dien_dien": 1}}
TICKET_PLAN = [{"ca_loc_nuong_trui": 3, "goi_bong_sung": 3},
               {"ca_loc_nuong_trui": 2, "lau_ca_linh_dien_dien": 2},
               {"goi_bong_sung": 2, "canh_chua_ca_loc": 2, "ca_keo_nuong": 2},
               {"lau_mam": 1, "ca_loc_nuong_trui": 2, "goi_bong_sung": 1},
               {"lau_mam": 1, "lau_ca_linh_dien_dien": 1, "ca_loc_nuong_trui": 1}]
TICKET_SHOP = {"oxygen": [{"level": 1, "price": 200, "oxygen_max_s": 45}, {"level": 2, "price": 400, "oxygen_max_s": 60}],
               "hp": [{"level": 1, "price": 250, "hp_max": 4}, {"level": 2, "price": 500, "hp_max": 5}]}
SHOP_NAME = {"oxygen": "Bình oxy", "hp": "Áo phao"}
SHOP_TICKS = 600


def kname(k):
    return KIND.get(k, (k, CREAM))[0]


def kcol(k):
    return KIND.get(k, (k, CREAM))[1]


class Game:
    def __init__(self):
        pyxel.init(W, H, title="Quan An Cho Noi", fps=60, quit_key=pyxel.KEY_NONE)  # Esc dùng để tạm dừng
        meta = json.load(open(os.path.join(ASSETS, "frames.json")))
        pyxel.colors[:] = meta["colors"]
        self.swim_fr, self.quan_fr = meta["swim"], meta["quan"]
        pyxel.images[0].load(0, 0, os.path.join(ASSETS, "ut_sen_swim.png"))
        pyxel.images[1].load(0, 0, os.path.join(ASSETS, "ut_sen_quan.png"))
        self.font = pyxel.Font(os.path.join(ASSETS, "ark-pixel-10px-proportional-latin.bdf"))
        self.tuning = load_contract(os.path.join(ROOT, "game.contract.json"))["tuning"]
        self.recipes = {d: m["recipe"] for d, m in self.tuning["menu"].items()}
        for d, r in TICKET_MENU.items():
            self.recipes.setdefault(d, r)
        self.shop = self.tuning.get("shop", {}).get("upgrades") or TICKET_SHOP
        self.seen = set()
        self.to_menu()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------ vòng đời
    def to_menu(self):
        self.scene, self.sess, self.error, self.help, self.paused = "menu", None, None, None, False
        self.menu_i = 0
        self.toasts = []
        self.facing, self.dir = 1, "down"

    def new_game(self):
        self.day = 1
        self.money = self.earned = 0
        self.rep = float(self.tuning["quan"].get("reputation_initial", 3.0))
        self.levels = {k: 0 for k in self.shop}      # cấp đã mua
        self.active = dict(self.levels)              # cấp đang áp dụng (mua hôm nay, hiệu lực từ Ngày kế)
        self.sold = Counter()
        self.history = []
        self.day_intro()

    def plan(self):
        plans = self.tuning.get("day_plan")
        if plans:
            return dict(plans[self.day - 1]["dishes"])
        return TICKET_PLAN[self.day - 1]

    def need(self):
        n = Counter()
        for d, q in self.plan().items():
            for k, c in self.recipes.get(d, {}).items():
                n[k] += c * q
        return dict(n)

    def day_intro(self):
        self.scene, self.timer = "day_intro", 240
        self.toasts = []

    def day_tuning(self):
        """Nâng cấp đang hiệu lực → tuning của Ngày (dữ liệu, không đổi luật)."""
        t = copy.deepcopy(self.tuning)
        for k, lv in self.active.items():
            if lv:
                row = self.shop[k][lv - 1]
                if "oxygen_max_s" in row:
                    t["gather"]["oxygen_max_s"] = row["oxygen_max_s"]
                if "hp_max" in row:
                    t["gather"]["hp_max"] = row["hp_max"]
        return t

    def start(self, mode):
        inv = self.inventory if mode == "quan" else None
        self.sess = Session(mode, self.day_tuning(), {}, SEED + self.day - 1, inv)
        self.inputs = LiveInputs()
        self.snap = self.sess.snapshot()
        self.scene = mode
        self.toasts = []
        if mode == "quan":
            self.stats = {"served": 0, "left": 0, "tips": 0, "paid": 0, "no_dish": 0, "rep0": self.snap.get("reputation", 0)}
        if mode not in self.seen:
            self.seen.add(mode)
            self.help = mode

    def end_quan(self):
        s = self.snap
        delta = s.get("reputation", 0) - self.stats["rep0"]
        lo, hi = 0.0, 5.0
        self.rep = round(min(hi, max(lo, self.rep + delta)), 2)
        self.money += s.get("money", 0)
        self.earned += s.get("earned", s.get("money", 0))
        self.stats["rep_delta"] = delta
        self.stats["shift_money"] = s.get("money", 0)
        self.history.append(self.stats)
        self.scene = "day_result"

    def open_shop(self):
        self.scene, self.timer, self.shop_i = "shop", SHOP_TICKS, 0

    def close_shop(self):
        self.active = dict(self.levels)
        if self.day >= DAYS:
            self.scene = "summary"
        else:
            self.day += 1
            self.day_intro()

    def score(self):
        return self.earned + 100 * math.floor(self.rep + 1e-9)

    def update(self):
        if self.help:
            if pyxel.btnp(pyxel.KEY_X) or pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_H):
                self.help = None
            return
        playing = self.scene in ("gather", "quan", "shop")
        if playing and (pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.KEY_P)):
            self.paused, self.pause_i = not self.paused, 0
            return
        if self.paused:
            return self.update_pause()
        if self.scene in ("gather", "quan") and pyxel.btnp(pyxel.KEY_H):
            self.help = self.scene
            return
        go = pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_E)
        if self.scene == "menu":
            if pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W) or pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.KEY_S):
                self.menu_i = 1 - self.menu_i
            elif pyxel.btnp(pyxel.KEY_RETURN):
                self.new_game() if self.menu_i == 0 else pyxel.quit()
        elif self.scene == "day_intro":
            self.timer -= 1
            if go or self.timer <= 0:
                self.start("gather")
        elif self.scene == "evening_intro":
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.start("quan")
        elif self.scene == "day_result":
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.open_shop()
        elif self.scene == "shop":
            self.update_shop()
        elif self.scene == "summary":
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.to_menu()
        elif self.scene in ("gather", "quan"):
            self.tick()

    def update_pause(self):
        if pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W) or pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.KEY_S):
            self.pause_i = 1 - self.pause_i
        elif pyxel.btnp(pyxel.KEY_RETURN):
            self.paused = False
            if self.pause_i == 1:
                self.to_menu()

    def update_shop(self):
        keys = list(self.shop)
        if pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W):
            self.shop_i = (self.shop_i - 1) % (len(keys) + 1)
        elif pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.KEY_S):
            self.shop_i = (self.shop_i + 1) % (len(keys) + 1)
        elif pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_E):
            if self.shop_i == len(keys):
                return self.close_shop()
            k = keys[self.shop_i]
            lv = self.levels[k]
            if lv >= len(self.shop[k]):
                self.toast("Đã nâng tối đa")
            elif self.money < self.shop[k][lv]["price"]:
                self.toast("Không đủ tiền")
            else:
                self.money -= self.shop[k][lv]["price"]
                self.levels[k] = lv + 1
                self.toast(f"Đã mua {SHOP_NAME.get(k, k)} cấp {lv + 1}, dùng từ Ngày kế")
        self.timer -= 1
        if self.timer <= 0:
            self.close_shop()
        self.toasts = [(m, t - 1) for m, t in self.toasts if t > 1]

    def tick(self):
        if self.sess.done or self.error:
            if pyxel.btnp(pyxel.KEY_RETURN):
                if self.scene == "gather":
                    self.inventory = self.sess.sim.inventory_items()
                    self.scene = "evening_intro"
                else:
                    self.end_quan()
            return
        dx = (pyxel.btn(pyxel.KEY_D) or pyxel.btn(pyxel.KEY_RIGHT)) - (pyxel.btn(pyxel.KEY_A) or pyxel.btn(pyxel.KEY_LEFT))
        dy = (pyxel.btn(pyxel.KEY_S) or pyxel.btn(pyxel.KEY_DOWN)) - (pyxel.btn(pyxel.KEY_W) or pyxel.btn(pyxel.KEY_UP))
        if self.scene == "quan":
            dy = -dy  # quán: z hướng bắc (lên màn hình)
        if dx:
            self.facing = 1 if dx > 0 else -1
        self.dir = "side" if dx else ("down" if dy else self.dir)
        self.inputs.set(move=(dx, dy), interact=pyxel.btn(pyxel.KEY_E), catch=pyxel.btn(pyxel.KEY_SPACE))
        try:
            for row in self.sess.step(self.inputs.advance()):
                self.on_event(row["name"], row.get("data") or {})
        except Exception as e:  # luật của nhóm lỗi: hiện lên màn hình thay vì sập cửa sổ
            self.error = f"{type(e).__name__}: {e}"
        self.snap = self.sess.snapshot()
        self.toasts = [(m, t - 1) for m, t in self.toasts if t > 1]

    def toast(self, msg):
        self.toasts = (self.toasts + [(msg, 150)])[-3:]

    def on_event(self, name, d):
        st = getattr(self, "stats", None)
        if self.scene == "quan" and st is not None:
            if name == "served":
                st["served"] += 1
                st["tips"] += d.get("tip") or 0
                self.sold[d.get("dish_id")] += 1
            elif name == "customer_left":
                st["left"] += 1
            elif name == "paid":
                st["paid"] += d.get("amount") or 0
            elif name == "no_dish":
                st["no_dish"] += 1
        msg = {
            "gather": lambda: f"Hái được {kname(d.get('kind'))}",
            "hold_full": lambda: "Giỏ không đủ chỗ, về Bến thôi!",
            "fish_caught": lambda: f"Bắt được đàn {kname(d.get('kind'))} (+{d.get('yield', d.get('quantity', '?'))})",
            "oxygen_empty": lambda: "Hết hơi! Nổi lên mau!",
            "choke": lambda: "Sặc nước! Mất 1 Máu",
            "monster_hit": lambda: f"Cá Sấu cắn! Mất 1 Máu, rơi {len(d.get('lost') or [])} món",
            "faint": lambda: "Út Sen ngất... mất hết giỏ",
            "customer_arrived": lambda: f"Khách vô! Gọi {DISH.get(d.get('dish_id'), d.get('dish_id'))}",
            "no_dish": lambda: "Khách vô mà kho hết món...",
            "dish_ready": lambda: "Má Tư: Bếp chín rồi con!",
            "served": lambda: "Dọn món xong" + (f", boa {d['tip']}k" if d.get("tip") else ""),
            "paid": lambda: f"Khách trả {d.get('amount', '?')}k",
            "customer_left": lambda: "Khách chờ lâu quá, bỏ về! Uy tín giảm",
            "cook_started": lambda: f"Bắt đầu nấu {SHORT.get(d.get('dish_id'), 'món')}",
            "dish_picked": lambda: f"Đã bưng {SHORT.get(d.get('dish_id'), 'món')}, mang ra bàn!",
        }.get(name)
        if msg:
            self.toast(msg())

    # ------------------------------------------------------------------ vẽ chung
    def text(self, x, y, s, col=CREAM, shadow=True):
        if shadow:
            pyxel.text(x + 1, y + 1, s, INK, self.font)
        pyxel.text(x, y, s, col, self.font)

    def ctext(self, y, s, col=CREAM, shadow=True):
        self.text((W - self.font.text_width(s)) // 2, y, s, col, shadow)

    def panel(self, x, y, w, h):
        pyxel.rect(x, y, w, h, WOOD_DK)
        pyxel.rectb(x, y, w, h, BAMBOO)

    def heart(self, x, y, full):
        c = RED if full else IND_DK
        pyxel.rect(x, y + 1, 7, 2, c); pyxel.rect(x + 1, y, 2, 4, c); pyxel.rect(x + 4, y, 2, 4, c)
        pyxel.rect(x + 1, y + 3, 5, 1, c); pyxel.rect(x + 2, y + 4, 3, 1, c); pyxel.pset(x + 3, y + 5, c)

    def clock(self, ticks):
        s = math.ceil(max(0, ticks or 0) / 60)
        return f"{s // 60}:{s % 60:02d}"

    def fish_sprite(self, x, y, d, kind):
        """Cá nhìn ngang, đầu theo hướng d (1 phải, -1 trái), đuôi vẫy."""
        flap = (pyxel.frame_count // 6 + x) % 2
        if kind == "ca_linh":
            pyxel.elli(x - 3, y - 1, 7, 3, GLASS)
            pyxel.tri(x - 3 * d, y, x - 6 * d, y - 2 - flap, x - 6 * d, y + 2 - flap, GLASS)
            pyxel.pset(x + 2 * d, y - 1, INK)
        else:
            pyxel.elli(x - 6, y - 2, 13, 5, PALM)
            pyxel.tri(x - 6 * d, y, x - 10 * d, y - 3 + flap, x - 10 * d, y + 3 + flap, PALM)
            pyxel.line(x - 2, y - 3, x + 2, y - 3, PALM)
            pyxel.pset(x + 4 * d, y - 1, INK)

    def hud_clock(self, prefix, ticks):
        low = (ticks or 0) <= 30 * 60
        col = (RED if (pyxel.frame_count // 15) % 2 else LANTERN) if low else CREAM
        self.text(4, 2, prefix + self.clock(ticks), col)

    def croc(self, x, y, d, state):
        """Cá Sấu Năm Chèo nhìn ngang, đầu theo hướng d."""
        stun = state in ("stunned", "recoil")
        body = MUD if stun else PALM
        pyxel.elli(x - 14, y - 3, 28, 7, body)
        pyxel.tri(x - 14 * d, y, x - 22 * d, y - 2, x - 22 * d, y + 3, body)        # đuôi
        jaw = 2 if (pyxel.frame_count // 10) % 2 and state == "chase" else 0
        pyxel.rect(x + (12 if d > 0 else -20), y - 2 - jaw, 8, 2, body)              # hàm trên
        pyxel.rect(x + (12 if d > 0 else -20), y + 1, 8, 2, body)                    # hàm dưới
        for i in range(-10, 10, 4):
            pyxel.pset(x + i, y - 4, HAIR)                                             # vảy lưng
        pyxel.pset(x + 9 * d, y - 3, RED if state == "chase" else LANTERN)            # mắt
        pyxel.line(x - 6, y + 4, x - 8, y + 6, body); pyxel.line(x + 6, y + 4, x + 8, y + 6, body)

    def item_icon(self, x, y, k):
        pyxel.circ(x + 3, y + 3, 3, kcol(k))
        pyxel.circb(x + 3, y + 3, 3, INK)

    def draw(self):
        getattr(self, "draw_" + self.scene)()
        for i, (m, t) in enumerate(self.toasts):
            y = 134 - (len(self.toasts) - 1 - i) * 14
            self.panel(4, y - 1, self.font.text_width(m) + 8, 13)
            self.text(8, y, m, LANTERN if i == len(self.toasts) - 1 else CREAM, shadow=False)
        if self.error:
            self.panel(10, 70, W - 20, 40)
            self.text(16, 74, "Luật báo lỗi. Esc → Về menu để chơi lại.", RED)
            self.text(16, 88, self.error[:60], CREAM)
        if self.help:
            self.draw_help()
        if self.paused:
            self.draw_pause()

    # ------------------------------------------------------------------ màn đầu/cuối
    # cảnh dưới sông cho màn chờ: (x, pha, tốc độ, loại) — cố định để mỗi lần mở đều giống nhau
    TITLE_FISH = [(40, 0, 0.55, "linh"), (52, 18, 0.55, "linh"), (46, 34, 0.55, "linh"),
                  (118, 70, 0.4, "loc"), (205, 20, 0.6, "linh"), (214, 36, 0.6, "linh"),
                  (178, 110, 0.35, "loc"), (270, 60, 0.5, "linh"), (282, 76, 0.5, "linh")]
    TITLE_WEED = [8, 15, 64, 71, 100, 140, 196, 232, 239, 290, 298, 312]
    TITLE_ROCK = [(28, 10), (124, 14), (258, 12)]

    def draw_title(self):
        fc = pyxel.frame_count
        SURF, FLOOR = 50, 160
        # trời bình minh + mặt trời + bờ dừa nước
        pyxel.cls(DAWN)
        pyxel.circ(296, 32, 11, LANTERN)
        for x in range(0, W, 9):
            h = 4 + (x * 7) % 5
            pyxel.tri(x, SURF, x + 4, SURF - h, x + 9, SURF, PALM)
        # nước theo tầng sâu, chuyển tầng bằng dither cho mềm
        for y0, y1, c in ((SURF, 95, SILT), (95, 130, MUD), (130, FLOOR, HAIR)):
            pyxel.rect(0, y0, W, y1 - y0, c)
        for y, c in ((95, SILT), (130, MUD)):
            pyxel.dither(0.5); pyxel.rect(0, y, W, 6, c); pyxel.dither(1.0)
        pyxel.line(0, SURF, W, SURF, CREAM)
        for x in range(0, W, 16):  # gợn sóng mặt nước
            pyxel.line((x + fc // 4) % W, SURF + 2, (x + fc // 4) % W + 5, SURF + 2, CREAM)
        # luồng nước: vệt sáng trôi ngang, uốn nhẹ
        pyxel.dither(0.5)
        for i in range(10):
            y = 60 + i * 9 + int(2 * math.sin(fc / 30 + i))
            x = (fc * (0.6 + i % 3 * 0.25) + i * 53) % (W + 40) - 20
            pyxel.line(x, y, x + 10 + i % 3 * 4, y, GLASS if y < 95 else SILT)
        pyxel.dither(1.0)
        # đáy: bùn + cát lấm tấm + đá rêu
        pyxel.rect(0, FLOOR, W, H - FLOOR, WOOD_DK)
        for i in range(0, W, 5):
            pyxel.pset(i, FLOOR + 2 + (i * 13) % 15, SILT if i % 3 else BAMBOO)
        for x, r in self.TITLE_ROCK:
            pyxel.elli(x, FLOOR - r // 2, r * 2, r, MUD)
            for k in range(0, r * 2, 3):
                pyxel.pset(x + k, FLOOR - r // 2 + (k % 2), PALM)
        # rong: lắc theo dòng, ngọn lắc nhiều hơn gốc
        for x in self.TITLE_WEED:
            n = 14 + x % 13
            px, py = x, FLOOR + 1
            for s in range(n):
                nx = x + math.sin(fc / 35 + x + s * 0.35) * s * 0.35
                pyxel.line(px, py, nx, FLOOR - s * 2, PALM)
                px, py = nx, FLOOR - s * 2
        # Út Sen bơi giữa sông, bọt khí nổi lên
        bob = int(2 * math.sin(fc / 25))
        ux, uy = 146, 104 + bob
        for i in range(4):
            by = uy - ((fc * 0.5 + i * 14) % 52)
            pyxel.circb(ux + 26 + int(2 * math.sin(fc / 9 + i)), by, 1, CREAM)
        f = self.swim_fr[(fc // 8) % 4]
        pyxel.blt(ux, uy, 0, f[0], f[1], f[2], f[3], KEY)
        # cá bơi ngang (đầu theo hướng bơi), trồi dần từ đáy lên và băng qua người
        for i, (x0, ph, sp, kind) in enumerate(self.TITLE_FISH):
            d = 1 if i % 2 == 0 else -1
            x = (x0 + d * fc * sp) % (W + 40) - 20
            y = FLOOR - 6 - (fc * sp * 0.25 + ph * 3) % (FLOOR - SURF - 12) + int(1.5 * math.sin((fc + ph) / 15))
            self.fish_sprite(x, y, d, "ca_linh" if kind == "linh" else "ca_loc")
        # bảng hiệu quán: chữ màu sáng trên gỗ tối, không đổ bóng
        sx, sw = 54, 212
        pyxel.line(sx + 20, 0, sx + 20, 6, BAMBOO); pyxel.line(sx + sw - 20, 0, sx + sw - 20, 6, BAMBOO)
        pyxel.rect(sx, 6, sw, 32, WOOD_DK)
        pyxel.rectb(sx, 6, sw, 32, BAMBOO)
        self.ctext(9, "QUÁN ĂN CHỢ NỔI", LANTERN, shadow=False)
        self.ctext(23, "Sáng lặn bắt cá, hái bông. Tối mở quán.", CREAM, shadow=False)

    # ------------------------------------------------------------------ menu + màn chuyển pha
    def choice(self, x, y, items, idx):
        for i, label in enumerate(items):
            on = i == idx
            if on:
                pyxel.rect(x - 4, y + i * 15 - 2, self.font.text_width(label) + 20, 14, LANTERN)
                pyxel.tri(x - 1, y + i * 15 + 1, x - 1, y + i * 15 + 7, x + 3, y + i * 15 + 4, INK)
            self.text(x + 8, y + i * 15, label, INK if on else CREAM, shadow=not on)

    def draw_menu(self):
        self.draw_title()
        self.panel(118, 120, 84, 38)
        self.choice(126, 125, ["Chơi", "Thoát"], self.menu_i)
        self.text(4, 168, "W/S chọn · Enter", CREAM, shadow=True)

    def screen(self, title, col=LANTERN, bg=IND_DK):
        pyxel.cls(bg)
        for i in range(0, H, 8):  # gợn nước
            pyxel.line((i * 37 + pyxel.frame_count // 3) % W, i, (i * 37 + pyxel.frame_count // 3) % W + 10, i, IND)
        self.panel(14, 8, W - 28, H - 16)
        self.ctext(13, title, col, shadow=False)
        pyxel.line(24, 26, W - 25, 26, BAMBOO)

    def ingredient_rows(self, x, y, have, need, cols=2):
        keys = list(need) + [k for k in have if k not in need]
        for i, k in enumerate(keys):
            cx, cy = x + (i % cols) * 140, y + (i // cols) * 13
            self.item_icon(cx, cy + 2, k)
            h, n = have.get(k, 0), need.get(k)
            col = CREAM if n is None else (PALM if h >= n else LANTERN)
            self.text(cx + 10, cy, f"{kname(k)} {h}/{n}" if n is not None else f"{kname(k)} ×{h}", col, shadow=False)
        return y + ((len(keys) + cols - 1) // cols) * 13

    def draw_day_intro(self):
        self.screen(f"NGÀY {self.day}/{DAYS} · SÁNG", LANTERN)
        self.text(24, 31, "Má Tư: \"Hôm nay quán bán mấy món này nghe con\":", CREAM, shadow=False)
        y = 46
        for d, q in self.plan().items():
            self.text(34, y, f"{DISH.get(d, d)} ×{q}", LANTERN, shadow=False)
            y += 12
        self.text(24, y + 4, "Cần mang về:", GLASS, shadow=False)
        self.ingredient_rows(34, y + 18, {}, self.need())
        lv = [f"{SHOP_NAME.get(k, k)} cấp {v}" for k, v in self.active.items() if v]
        if lv:
            self.text(24, H - 36, "Đang dùng: " + ", ".join(lv), PALM, shadow=False)
        bar = int((W - 60) * self.timer / 240)
        pyxel.rect(30, H - 20, bar, 2, LANTERN)
        self.text(W - 120, H - 30, "Enter: xuống sông", CREAM, shadow=False)

    def draw_evening_intro(self):
        self.screen(f"NGÀY {self.day}/{DAYS} · CHIỀU VỀ, MỞ QUÁN", LANTERN)
        items = self.inventory or {}
        self.text(24, 31, "Nhập kho:" if items else "Nhập kho: trống (về tay không)", GLASS, shadow=False)
        y = self.ingredient_rows(34, 45, items, {}) + 4
        self.text(24, y, "Tối nay nấu được:", GLASS, shadow=False)
        can = [d for d in self.plan() if all(items.get(k, 0) >= q for k, q in self.recipes.get(d, {}).items())]
        for i, d in enumerate(can or [None]):
            self.text(34, y + 14 + i * 12, DISH.get(d, d) if d else "(chưa đủ đồ nấu món nào)", CREAM if d else RED, shadow=False)
        self.text(W - 130, H - 30, "Enter: mở quán", LANTERN, shadow=False)

    def draw_day_result(self):
        st = self.history[-1] if self.history else {}
        self.screen(f"KẾT QUẢ NGÀY {self.day}", LANTERN, INK)
        rd = st.get("rep_delta", 0)
        rows = [("Khách đã phục vụ", st.get("served", 0), PALM),
                ("Khách bỏ về", st.get("left", 0), RED if st.get("left") else CREAM),
                ("Tiền ca", f"{st.get('shift_money', 0)}k", LANTERN),
                ("Tiền boa", f"{st.get('tips', 0)}k", LANTERN),
                ("Uy tín", f"{'+' if rd >= 0 else ''}{rd:.1f}  →  {self.rep:.1f}", PALM if rd >= 0 else RED),
                ("Tổng tiền", f"{self.money}k", CREAM)]
        for i, (k, v, c) in enumerate(rows):
            self.text(40, 36 + i * 15, k, CREAM, shadow=False)
            self.text(190, 36 + i * 15, str(v), c, shadow=False)
        self.text(W - 120, H - 30, "Enter: ra chợ mua đồ", LANTERN, shadow=False)

    def draw_shop(self):
        self.screen("CHỢ: NÂNG CẤP CHO NGÀY MAI", LANTERN, INK)
        self.text(24, 30, f"Tiền: {self.money}k", LANTERN, shadow=False)
        self.text(W - 104, 30, f"Đóng sau {math.ceil(self.timer / 60)}s", CREAM, shadow=False)
        keys = list(self.shop)
        labels = []
        for k in keys:
            lv, rows = self.levels[k], self.shop[k]
            if lv >= len(rows):
                labels.append(f"{SHOP_NAME.get(k, k)}: tối đa")
            else:
                r = rows[lv]
                eff = f"oxy {r['oxygen_max_s']}s" if "oxygen_max_s" in r else f"{r.get('hp_max')} Máu"
                labels.append(f"{SHOP_NAME.get(k, k)} cấp {lv + 1}: {eff} · {r['price']}k")
        self.choice(36, 50, labels + ["Xong, sang Ngày kế"], self.shop_i)
        self.text(24, H - 30, "W/S chọn · Enter mua · cấp mới dùng từ Ngày kế", GLASS, shadow=False)

    def draw_summary(self):
        self.screen("TỔNG KẾT 5 NGÀY", LANTERN, INK)
        best = self.sold.most_common(1)
        rows = [("Tổng tiền thu", f"{self.earned}k"), ("Tiền còn", f"{self.money}k"),
                ("Uy tín", f"{self.rep:.1f}"), ("Điểm", str(self.score())),
                ("Món bán chạy", f"{DISH.get(best[0][0], best[0][0])} ×{best[0][1]}" if best else "chưa bán món nào")]
        for i, (k, v) in enumerate(rows):
            self.text(40, 40 + i * 16, k, CREAM, shadow=False)
            self.text(170, 40 + i * 16, v, LANTERN, shadow=False)
        self.text(W - 120, H - 30, "Enter: về menu", GLASS, shadow=False)

    def draw_pause(self):
        pyxel.dither(0.6); pyxel.rect(0, 0, W, H, INK); pyxel.dither(1.0)
        self.panel(100, 56, 120, 64)
        self.ctext(62, "TẠM DỪNG", LANTERN, shadow=False)
        self.choice(120, 82, ["Tiếp tục", "Về menu"], self.pause_i)

    # ------------------------------------------------------------------ buổi sáng
    def draw_gather(self):
        s, t = self.snap, self.tuning["gather"]
        X, D = t["bounds"]["x"][1], t["bounds"]["d"][1]
        S = 10                                   # 10 px = 1 m -> thấy 32 m sông
        p = s.get("player", {})
        px_, pd = p.get("pos", t["start_pos"])
        cam_x = max(-2, min(X + 2 - W / S, px_ - W / S / 2))
        cam_d = max(-5, min(D + 1 - (H - 16) / S, pd - (H - 16) / S * 0.6))
        sx = lambda x: int((x - cam_x) * S)
        sy = lambda d: int((d - cam_d) * S) + 16
        # trời + bờ dừa nước + nước theo tầng sâu + đáy bùn
        pyxel.cls(DAWN)
        surf = sy(0)
        pyxel.rect(0, surf - 3, W, 3, PALM)
        for band, (d0, d1, c) in enumerate(((0, 10, SILT), (10, 20, MUD), (20, D, HAIR))):
            pyxel.rect(0, sy(d0), W, sy(d1) - sy(d0), c)
        pyxel.rect(0, sy(D), W, H, WOOD_DK)
        pyxel.line(0, surf, W, surf, CREAM)
        # bến (ghe gỗ)
        dx, dd = t["dock_pos"]
        pyxel.rect(sx(dx - 2), sy(dd) - 4, 40, 4, BAMBOO); pyxel.rect(sx(dx - 1.5), sy(dd), 30, 2, WOOD_DK)
        self.text(sx(dx - 2), sy(dd) - 16, "Bến", WOOD_DK, shadow=False)
        # nút hái
        for n in s.get("nodes", []):
            x, y = sx(n["pos"][0]), sy(n["pos"][1])
            ready = n.get("ready", True)
            pyxel.elli(x - 5, y - 1, 11, 4, PALM if ready else MUD)
            pyxel.circ(x, y - 3, 3, kcol(n["kind"]) if ready else MUD)
            if not ready and n.get("regrow_ticks"):
                self.text(x - 6, y - 16, f"{math.ceil(n['regrow_ticks'] / 60)}s", WOOD_DK, shadow=False)
        # đàn cá: luật giữ đàn tại một điểm (vùng bắt), hình thì cho cá bơi vòng quanh điểm đó
        fc = pyxel.frame_count
        for f in s.get("fish", []):
            cx, cy = sx(f["pos"][0]), sy(f["pos"][1])
            seed = sum(map(ord, f.get("id", "")))
            school = 5 if f["kind"] == "ca_linh" else 1
            for k in range(school):
                a = fc / 45 + seed + k * 0.55
                r = 12 + (k % 2) * 4
                x, y = cx + int(r * math.cos(a)), cy + int(4 * math.sin(a)) + (k % 3 - 1) * 3
                self.fish_sprite(x, y, -1 if math.sin(a) > 0 else 1, f["kind"])
        danger = False
        mon = self.tuning["gather"].get("monsters", {}).get("species", {}).get("ca_sau", {})
        for mo in s.get("monsters", []):
            mx_, md_ = mo["pos"]
            near = math.hypot(mx_ - px_, md_ - pd) <= mon.get("detect_radius", 10)
            danger = danger or mo.get("state") == "chase" or (near and pd >= 10)
            self.croc(sx(mx_), sy(md_), 1 if px_ >= mx_ else -1, mo.get("state"))
        # Út Sen: lật theo hướng, viền kem khi xuống tầng sâu
        moving = abs(p.get("vel", [0, 0])[0]) + abs(p.get("vel", [0, 0])[1]) > 0.1
        fr = self.swim_fr[(pyxel.frame_count // 7) % 4 if moving else 0]
        if pd > 15:
            pyxel.pal(INK, CREAM)
        pyxel.blt(sx(px_) - fr[2] // 2, sy(pd) - fr[3] // 2, 0, fr[0], fr[1], fr[2] * self.facing, fr[3], KEY)
        pyxel.pal()
        here, target, nxt = self.gather_guide(s)
        if target:
            self.arrow(sx(target[0]), sy(target[1]) - 6)
        if here:
            self.bubble(sx(px_), sy(pd) - 30, here[0], here[1])
        cd = p.get("catch_cd_ticks", 0)
        if cd:  # hồi bắt cá
            cmax = self.tuning["gather"].get("catch_cooldown_s", 0.5) * 60
            pyxel.rect(sx(px_) - 8, sy(pd) - 9, max(1, int(16 * cd / cmax)), 1, GLASS)
        self.draw_oxy_alarm(p, sx(px_), sy(pd))
        if danger:
            on = (pyxel.frame_count // 10) % 2
            pyxel.dither(0.7 if on else 0.4)
            for i in range(4):
                pyxel.rectb(i, 16 + i, W - 2 * i, H - 16 - 2 * i, IND)
            pyxel.dither(1.0)
            self.bubble(W // 2 - 30, 44, "Thủy quái! Lên chỗ cạn (W)", CREAM, bg=IND)
        # HUD trên
        pyxel.rect(0, 0, W, 15, WOOD_DK); pyxel.line(0, 15, W, 15, BAMBOO)
        self.hud_clock(f"N{getattr(self, 'day', 1)} ", s.get("time_left_ticks"))
        if "oxygen_ticks" in p and p.get("oxygen_max_ticks"):
            frac = p["oxygen_ticks"] / p["oxygen_max_ticks"]
            self.text(66, 2, "Oxy", GLASS)
            for i in range(10):
                on = i < math.ceil(frac * 10 - 1e-9)
                pyxel.circ(92 + i * 7, 7, 2, (RED if frac < 0.25 else GLASS) if on else IND_DK)
        if "hp" in p:
            for i in range(p.get("hp_max", 3)):
                self.heart(166 + i * 9, 4, i < p["hp"])
        hold, cap = s.get("hold", []), s.get("hold_capacity", 12)
        x0 = W - 2 - cap * 6
        self.text(x0 - 22, 2, "Giỏ")
        for i in range(cap):
            pyxel.rect(x0 + i * 6, 4, 5, 7, BAMBOO if i >= len(hold) else kcol(hold[i]))
        # hàng 2: độ sâu + danh sách Má Tư cần (đã có/cần)
        pyxel.rect(0, 16, W - 68, 12, WOOD_DK)
        zone = "nông" if pd < 10 else "giữa" if pd < 20 else "sâu"
        self.text(4, 17, f"Sâu {pd:.0f}m {zone}", GLASS, shadow=False)
        have = Counter(hold)
        x = 82
        for k, n in (self.need() if hasattr(self, "day") else {}).items():
            self.item_icon(x, 19, k)
            self.text(x + 9, 17, f"{have.get(k, 0)}/{n}", PALM if have.get(k, 0) >= n else CREAM, shadow=False)
            x += 34
        # bản đồ nhỏ
        mx, my, mw, mh = W - 64, 20, 60, 20
        pyxel.rect(mx, my, mw, mh, SILT); pyxel.rectb(mx - 1, my - 1, mw + 2, mh + 2, WOOD_DK)
        m = lambda x, d: (mx + int(x / X * (mw - 1)), my + int(d / D * (mh - 1)))
        for n in s.get("nodes", []):
            pyxel.pset(*m(*n["pos"]), kcol(n["kind"]) if n.get("ready", True) else MUD)
        for f in s.get("fish", []):
            pyxel.pset(*m(*f["pos"]), INK)
        pyxel.circ(*m(px_, pd), 1, RED)
        self.footer(H - 14, nxt)
        if self.sess.done:
            self.end_banner(f"Hết buổi sáng: {s.get('reason') or self.sess.sim.reason}")

    def draw_oxy_alarm(self, p, x, y):
        if "oxygen_ticks" not in p or not p.get("oxygen_max_ticks") or p.get("at_surface"):
            return
        frac = p["oxygen_ticks"] / p["oxygen_max_ticks"]
        # thanh oxy ngay trên đầu Út Sen khi ở dưới nước
        col = GLASS if frac >= 0.5 else LANTERN if frac >= 0.25 else RED
        pyxel.rect(x - 9, y - 14, 18, 4, INK)
        pyxel.rect(x - 8, y - 13, int(16 * frac), 2, col)
        if frac >= 0.25:
            return
        severe = frac < 0.10
        on = (pyxel.frame_count // (8 if severe else 16)) % 2
        pyxel.dither(0.6 if on else 0.3)
        for i in range(6 if severe else 3):
            pyxel.rectb(i, 16 + i, W - 2 * i, H - 16 - 2 * i, RED)
        pyxel.dither(1.0)
        if frac <= 0:
            msg = "Hết hơi! Giữ W nổi lên ngay"
        elif severe:
            msg = "NỔI LÊN NGAY! (giữ W)"
        else:
            msg = "Oxy sắp hết! Bấm W nổi lên"
        if on or not severe:
            self.bubble(W // 2 - 30, 20, msg, CREAM, bg=RED)

    def end_banner(self, msg):
        self.panel(60, 70, 200, 36)
        self.ctext(75, msg, LANTERN)
        self.ctext(89, "Nhấn Enter")

    # ------------------------------------------------------------------ hướng dẫn + gợi ý
    HELP = {
        "gather": ("BUỔI SÁNG: LẶN KIẾM ĐỒ NẤU", [
            ("Mục tiêu: gom đồ vào giỏ, rồi về Bến để mở quán.", CREAM),
            ("WASD / mũi tên: bơi. S lặn xuống, W nổi lên.", CREAM),
            ("E ở mặt nước: hái bông (vàng, đỏ).", LANTERN),
            ("Space dưới nước: bắt đàn cá.", GLASS),
            ("E ở Bến: kết thúc buổi sáng, mang giỏ về.", CREAM),
            ("Hết Oxy thì sặc; Cá Sấu chỗ sâu cắn: mất Máu.", RED),
            ("Hết Máu: ngất, mất giỏ.  Esc/P: tạm dừng.", RED)]),
        "quan": ("BUỔI TỐI: MỞ QUÁN", [
            ("Khách ngồi vào Bàn, khung trên đầu là món gọi.", CREAM),
            ("1. Tới Bếp, bấm E: nấu món khách gọi.", LANTERN),
            ("2. Chờ chín (đếm giây), bấm E: lấy món.", LANTERN),
            ("3. Mang tới Bàn, bấm E: dọn món.", LANTERN),
            ("Khách ăn xong tự trả tiền. Dọn nhanh có boa.", CREAM),
            ("Vạch màu dưới món gọi: khách còn chờ được bao lâu.", CREAM),
            ("Chờ quá lâu: khách bỏ về, mất uy tín. Esc/P: dừng.", RED)]),
    }

    def draw_help(self):
        title, lines = self.HELP[self.help]
        pyxel.dither(0.7); pyxel.rect(0, 0, W, H, INK); pyxel.dither(1.0)
        self.panel(14, 10, W - 28, H - 20)
        self.ctext(15, title, LANTERN, shadow=False)
        pyxel.line(24, 28, W - 25, 28, BAMBOO)
        for i, (line, col) in enumerate(lines):
            self.text(24, 33 + i * 13, line, col, shadow=False)
        if (pyxel.frame_count // 30) % 2:
            self.ctext(H - 24, "X hoặc Enter: vào chơi  ·  H: xem lại", GLASS, shadow=False)

    def bubble(self, cx, y, msg, col=LANTERN, bg=None):
        w = self.font.text_width(msg) + 8
        x = max(2, min(W - w - 2, cx - w // 2))
        y = max(17, y)  # không chui dưới thanh HUD
        self.panel(x, y, w, 13)
        if bg is not None:
            pyxel.rect(x + 1, y + 1, w - 2, 11, bg)
        self.text(x + 4, y + 1, msg, col, shadow=False)

    def footer(self, y, nxt):
        line, hint = "Việc tiếp: " + nxt, "H: hướng dẫn"
        self.text(4, y, line, LANTERN)
        if self.font.text_width(line) + self.font.text_width(hint) + 16 < W:  # chỉ hiện khi còn chỗ
            self.text(W - self.font.text_width(hint) - 4, y, hint, GLASS)

    def arrow(self, x, y):
        if (pyxel.frame_count // 15) % 2:
            pyxel.tri(x - 4, y - 7, x + 4, y - 7, x, y - 2, LANTERN)
            pyxel.trib(x - 4, y - 7, x + 4, y - 7, x, y - 2, INK)

    def gather_guide(self, s):
        """(gợi ý tại chỗ, toạ độ mục tiêu kế, việc tiếp) — chỉ để hiển thị, không đổi luật."""
        t, p = self.tuning["gather"], s.get("player", {})
        pos = p.get("pos", t["start_pos"])
        surf = p.get("at_surface", pos[1] <= t["surface_depth"])
        dist = lambda q: math.hypot(q[0] - pos[0], q[1] - pos[1])
        hold, cap = len(s.get("hold", [])), s.get("hold_capacity", 12)
        nodes = [n for n in s.get("nodes", []) if n.get("ready", True)]
        fish = s.get("fish", [])
        here = None
        if dist(t["dock_pos"]) <= t["dock_radius"]:
            here = ("E: về quán (hết buổi sáng)", LANTERN) if hold else ("Giỏ trống! Đừng bấm E ở Bến", RED)
        if surf:
            near = [n for n in nodes if dist(n["pos"]) <= t["interact_radius"]]
            if near:
                here = (f"E: hái {kname(min(near, key=lambda n: dist(n['pos']))['kind'])}", LANTERN)
        elif p.get("catch_cd_ticks", 0) == 0:
            near = [f for f in fish if dist(f["pos"]) <= t["catch_radius"]]
            if near:
                here = (f"Space: bắt {kname(min(near, key=lambda f: dist(f['pos']))['kind'])}", GLASS)
        o2, o2max = p.get("oxygen_ticks"), p.get("oxygen_max_ticks")
        if not surf and o2 is not None and o2max and o2 / o2max < 0.25:
            return here, [pos[0], 0], "Nổi lên lấy hơi: giữ W"
        if hold >= cap or (hold and (s.get("time_left_ticks") or 0) < 30 * 60):
            return here, t["dock_pos"], "Về Bến, bấm E để mở quán"
        goals = nodes + fish
        if hasattr(self, "day"):  # ưu tiên thứ Má Tư còn thiếu
            have = Counter(s.get("hold", []))
            want = [o for o in goals if have.get(o["kind"], 0) < self.need().get(o["kind"], 0)]
            goals = want or goals
        if not goals:
            return here, t["dock_pos"], "Hết đồ để gom: về Bến, bấm E"
        g = min(goals, key=lambda o: dist(o["pos"]))
        how = "nổi lên, bấm E hái" if g in nodes else "lặn tới, bấm Space bắt"
        return here, g["pos"], f"Tới {kname(g['kind'])} ({how})"

    def quan_guide(self, s):
        t, p = self.tuning["quan"], s.get("player", {})
        pos = p.get("pos", t["start_pos"])
        dist = lambda q: math.hypot(q[0] - pos[0], q[1] - pos[1])
        hand = s.get("hand")
        stoves, tables = s.get("stoves", []), s.get("tables", [])
        custs = s.get("customers", [])
        dname = lambda d: SHORT.get(d, d)
        todo = [c for c in custs if c.get("state") == "waiting" and c.get("base_price") is None]
        here = None
        objs = [(dist(o["pos"]), 0, o) for o in stoves] + [(dist(o["pos"]), 1, o) for o in tables]
        objs = [o for o in objs if o[0] <= t["interact_radius"]]
        if objs:
            _, is_table, o = min(objs, key=lambda o: (o[0], o[1]))
            if not is_table:
                st = o.get("state")
                if st == "cooking":
                    here = (f"Đang nấu... {math.ceil(o.get('cook_ticks_left', 0) / 60)}s", CREAM)
                elif st == "ready" and not hand:
                    here = (f"E: lấy {dname((o.get('dish') or {}).get('dish_id'))}", LANTERN)
                elif st == "idle" and todo and not hand:
                    here = (f"E: nấu {dname(todo[0]['dish_id'])}", LANTERN)
            else:
                c = next((c for c in custs if c.get("table_id") == o["id"]), None)
                if c and hand and c.get("state") == "waiting":
                    here = (f"E: dọn {dname(hand.get('dish_id'))}", LANTERN)
        pos_of = {o["id"]: o["pos"] for o in stoves + tables}
        if hand:
            c = next((c for c in custs if c.get("id") == hand.get("order_id")), None)
            return here, pos_of.get(c["table_id"]) if c else None, f"Mang {dname(hand.get('dish_id'))} tới Bàn, bấm E"
        ready = [o for o in stoves if o.get("state") == "ready"]
        if ready:
            return here, ready[0]["pos"], "Món chín rồi: tới Bếp, bấm E lấy"
        cooking = [o for o in stoves if o.get("state") == "cooking"]
        if cooking:
            return here, None, f"Chờ bếp chín ({math.ceil(cooking[0].get('cook_ticks_left', 0) / 60)}s)"
        if todo:
            return here, stoves[0]["pos"] if stoves else None, f"Tới Bếp, E nấu {dname(todo[0]['dish_id'])}"
        if any(c.get("state") == "eating" for c in custs):
            return here, None, "Khách đang ăn, chờ trả tiền"
        if not s.get("stock"):
            return here, None, "Kho hết đồ, chờ hết ca"
        return here, None, "Chờ khách vô..."

    # ------------------------------------------------------------------ buổi tối
    def draw_stove(self, x, y, st):
        state, fc = st.get("state"), pyxel.frame_count
        pyxel.rect(x - 10, y - 3, 21, 12, SKIN_DK)               # lò đất
        pyxel.rectb(x - 10, y - 3, 21, 12, WOOD_DK)
        pyxel.rect(x - 4, y + 2, 9, 6, INK)                      # miệng lò
        if state in ("cooking", "ready"):
            pyxel.tri(x - 3, y + 7, x + 3, y + 7, x, y + 2 - (fc // 6) % 2, RED)
            pyxel.pset(x, y + 5, LANTERN)
        pyxel.elli(x - 8, y - 9, 17, 7, HAIR)                     # nồi
        pyxel.line(x - 7, y - 8, x + 7, y - 8, MUD)
        if state == "cooking":
            pyxel.dither(0.6)
            for i in range(3):
                pyxel.pset(x - 4 + i * 4 + (fc // 10 + i) % 2, y - 12 - (fc // 8 + i * 3) % 6, CREAM)
            pyxel.dither(1.0)
        if state == "cooking":  # tiến độ nấu
            dish = (st.get("dish") or {}).get("dish_id")
            total = self.tuning["menu"].get(dish, {}).get("cook_s", 0) * 60
            if total:
                pyxel.rect(x - 10, y + 10, 21, 3, INK)
                pyxel.rect(x - 9, y + 11, int(19 * (1 - st.get("cook_ticks_left", 0) / total)), 1, LANTERN)
        if state == "ready":
            pyxel.elli(x - 6, y - 9, 13, 3, LANTERN)
            self.text(x + 11, y - 12, "Chín!", LANTERN, shadow=True)
        self.text(x - 7, y + 14, st.get("id", "Bếp") if len(self.snap.get("stoves", [])) > 1 else "Bếp", CREAM, shadow=False)

    def draw_table(self, x, y, c, pat_max):
        pyxel.circ(x - 15, y + 3, 3, WOOD_DK); pyxel.circ(x + 15, y + 3, 3, WOOD_DK)   # ghế đẩu
        pyxel.rect(x - 11, y - 6, 23, 12, SKIN_DK)
        pyxel.rectb(x - 11, y - 6, 23, 12, WOOD_DK)
        self.text(x - 7, y + 8, "Bàn", CREAM, shadow=False)
        if not c:
            return
        cx, cy = x - 15, y - 2                                   # khách ngồi ghế trái
        pyxel.rect(cx - 4, cy - 1, 9, 8, IND)                    # áo
        pyxel.circ(cx, cy - 4, 3, SKIN)
        pyxel.tri(cx - 7, cy - 5, cx + 7, cy - 5, cx, cy - 12, LANTERN)   # nón lá
        pyxel.trib(cx - 7, cy - 5, cx + 7, cy - 5, cx, cy - 12, BAMBOO)
        if c.get("state") == "eating":
            pyxel.elli(x - 4, y - 3, 9, 5, CREAM); pyxel.elli(x - 2, y - 2, 5, 2, kcol("ca_loc"))
            self.text(cx - 4, cy - 26, "ngon...", CREAM, shadow=False)
            return
        name = DISH.get(c.get("dish_id"), c.get("dish_id") or "?")
        w = self.font.text_width(name) + 8
        bx = max(2, min(W - w - 2, cx - w // 2))
        self.panel(bx, cy - 31, w, 17)
        self.text(bx + 4, cy - 30, name, CREAM, shadow=False)
        pl = c.get("patience_ticks_left")
        if pl is not None and pat_max:
            frac = max(0.0, min(1.0, pl / pat_max))
            col = PALM if frac >= 0.5 else LANTERN if frac >= 0.25 else (RED if (pyxel.frame_count // 8) % 2 else CREAM)
            pyxel.rect(bx + 3, cy - 18, int((w - 6) * frac), 2, col)

    def draw_quan(self):
        s, t = self.snap, self.tuning["quan"]
        X, Z = t["bounds"]["x"][1], t["bounds"]["z"][1]
        S = 13                                   # sàn 208x130, chừa HUD trên + 2 dòng dưới
        ox, oy = (W - X * S) // 2, 18
        sx = lambda x: ox + int(x * S)
        sy = lambda z: oy + int((Z - z) * S)
        pyxel.cls(INK)
        for i in range(0, H, 6):  # nước đêm
            pyxel.line(0, i, W, i + 2, IND_DK)
        pyxel.rect(ox, oy, X * S, Z * S, BAMBOO)
        for yy in range(oy, oy + Z * S, 6):
            pyxel.line(ox, yy, ox + X * S - 1, yy, MUD)
        pyxel.rectb(ox - 1, oy - 1, X * S + 2, Z * S + 2, WOOD_DK)
        for i in range(X + 1):  # đèn dây
            on = (i + pyxel.frame_count // 30) % 3
            pyxel.circ(ox + i * S, oy - 1, 1, LANTERN if on else BAMBOO)
        for st in s.get("stoves", []):
            self.draw_stove(sx(st["pos"][0]), sy(st["pos"][1]), st)
        seated = {c.get("table_id"): c for c in s.get("customers", [])}
        for tb in s.get("tables", []):
            self.draw_table(sx(tb["pos"][0]), sy(tb["pos"][1]), seated.get(tb["id"]), t["patience_s"] * 60)
        # Út Sen: đi xuống / bưng món / đi ngang (lật trái)
        p = s.get("player", {})
        x, z = p.get("pos", t["start_pos"])
        moving = abs(p.get("vel", [0, 0])[0]) + abs(p.get("vel", [0, 0])[1]) > 0.1
        a = (pyxel.frame_count // 9) % 4 if moving else 0
        base = 4 if s.get("hand") else (8 if self.dir == "side" else 0)
        fr = self.quan_fr[base + a]
        flip = self.facing if base == 8 else 1
        pyxel.blt(sx(x) - fr[2] // 2, sy(z) - fr[3] + 4, 1, fr[0], fr[1], fr[2] * flip, fr[3], KEY)
        here, target, nxt = self.quan_guide(s)
        if target:
            self.arrow(sx(target[0]), sy(target[1]) - 14)
        if here:
            self.bubble(sx(x), sy(z) - fr[3] - 12, here[0], here[1])
        # HUD
        pyxel.rect(0, 0, W, 15, WOOD_DK); pyxel.line(0, 15, W, 15, BAMBOO)
        self.hud_clock(f"N{getattr(self, 'day', 1)} ", s.get("time_left_ticks"))
        self.text(60, 2, f"Ca {s.get('money', 0)}k", LANTERN)
        rep = s.get("reputation", 0)
        self.text(120, 2, f"Uy tín {rep:.1f}")
        for i in range(5):
            pyxel.circ(178 + i * 6, 7, 2, LANTERN if i < math.floor(rep) else IND_DK)
        hand = s.get("hand")
        hand_txt = SHORT.get(hand.get("dish_id"), "món") if isinstance(hand, dict) else (hand or "trống")
        self.text(212, 2, "Tay: " + str(hand_txt)[:16])
        stock = s.get("stock", {})
        self.footer(152, nxt)
        self.text(4, 166, "Kho: " + (", ".join(f"{kname(k)} ×{n}" for k, n in stock.items()) or "trống"))
        if self.sess.done:
            self.end_banner("Hết ca tối")

if __name__ == "__main__":
    Game()
