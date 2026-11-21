"""Út Sen trong quán (nhìn từ trên kiểu 3/4) — 16x22. Chạy: python build.py

Tags: down (đi xuống), carry (đi xuống, bưng món), side (đi sang phải; sang trái = lật khi blt).
Cùng quy ước màu với ut-sen-swim: chỉ viền dùng "ink".
"""
import os, sys
sys.path.insert(0, os.path.expanduser("~/.claude/skills/pixel-art-studio/scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ut-sen-swim"))
from pixelstudio import Sprite
from build import GAME as C   # bảng màu chung (file build của sprite lặn)

W, H = 16, 22
s = Sprite(W, H, palette=list(C.values()))
STEP = [0, 1, 0, -1]          # 1 = chân trái bước, -1 = chân phải bước
BOB = [0, 1, 0, 1]            # thân nhấc 1px ở khung chuyển chân


def checker(x0, x1, y0, y1, start=0):
    for yy in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            s.px(x, yy, C["cream"] if (x + yy + start) % 2 else C["hair"])


def front(step, bob, carry=False):
    y = -bob
    ly, ry = (1, 0) if step == 1 else (0, 1) if step == -1 else (0, 0)
    # chân + dép
    s.rect(6, 17 + y, 7, 18 + y + ly, C["indigo_dk"]); s.rect(9, 17 + y, 10, 18 + y + ry, C["indigo_dk"])
    s.rect(6, 19 + y + ly, 7, 19 + y + ly, C["wood_dk"]); s.rect(9, 19 + y + ry, 10, 19 + y + ry, C["wood_dk"])
    # áo bà ba: thân + vạt xẻ tà hai bên
    s.rect(5, 11 + y, 11, 16 + y, C["indigo"])
    s.px(4, 16 + y, C["indigo"]); s.px(12, 16 + y, C["indigo"])
    s.line(5, 16 + y, 11, 16 + y, C["indigo_dk"]); s.px(8, 16 + y, None)
    if carry:
        s.rect(4, 11 + y, 5, 12 + y, C["indigo"]); s.rect(11, 11 + y, 12, 12 + y, C["indigo"])
        s.px(4, 13 + y, C["skin"]); s.px(12, 13 + y, C["skin"])
        s.line(5, 13 + y, 11, 13 + y, C["cream"])          # miệng tô
        s.line(6, 12 + y, 10, 12 + y, C["red"]); s.px(8, 12 + y, C["palm"])  # món + rau thơm
        s.line(6, 14 + y, 10, 14 + y, C["cream"])
        s.line(7, 15 + y, 9, 15 + y, C["mud"])             # đáy tô tối
        s.px(7, 10 + y - bob, C["cream"]); s.px(9, 9 + y + bob, C["cream"])  # hơi nóng
    else:
        for by in (12, 14): s.px(8, by + y, C["cream"])     # hàng nút giữa ngực
        al, ar = (0, 1) if step == 1 else (1, 0) if step == -1 else (0, 0)
        s.rect(4, 12 + y, 4, 14 + y + al, C["indigo"]); s.rect(12, 12 + y, 12, 14 + y + ar, C["indigo"])
        s.px(4, 15 + y + al, C["skin"]); s.px(12, 15 + y + ar, C["skin"])
    # đầu: tóc ngang vai, khăn rằn quấn 2 hàng, nút thắt lệch phải
    s.circle(8, 6 + y, 4, C["skin"], fill=True)
    s.rect(5, 2 + y, 11, 3 + y, C["hair"])
    s.rect(4, 5 + y, 4, 10 + y, C["hair"]); s.rect(12, 5 + y, 12, 10 + y, C["hair"])
    for x in (5, 7, 9, 11): s.px(x, 5 + y, C["hair"])       # tóc mái
    checker(4, 12, 3 + y, 4 + y)
    s.px(13, 3 + y, C["cream"]); s.px(13, 4 + y, C["hair"]); s.px(13, 5 + y + bob, C["cream"])  # nút + đuôi khăn
    s.rect(6, 6 + y, 6, 7 + y, C["hair"]); s.rect(10, 6 + y, 10, 7 + y, C["hair"])  # mắt
    s.px(5, 8 + y, C["dawn"]); s.px(11, 8 + y, C["dawn"])  # má hồng
    s.px(8, 10 + y, C["skin_dk"])
    s.outline(C["ink"], where="outside")


def side(step, bob):
    """Quay phải. step: 0 đứng thẳng, ±1 sải chân."""
    y = -bob
    if step == 0:
        s.rect(7, 17 + y, 8, 19 + y, C["indigo_dk"]); s.rect(7, 19 + y, 9, 19 + y, C["wood_dk"])
    else:
        s.line(7, 17 + y, 5, 19 + y, C["indigo_dk"]); s.line(8, 17 + y, 10, 19 + y, C["indigo_dk"])
        s.px(6, 17 + y, C["indigo_dk"]); s.px(9, 17 + y, C["indigo_dk"])
        s.rect(4, 19 + y, 5, 19 + y, C["wood_dk"]); s.rect(10, 19 + y, 11, 19 + y, C["wood_dk"])
    s.rect(6, 11 + y, 10, 16 + y, C["indigo"])
    s.px(5, 16 + y - (step != 0), C["indigo"])              # vạt sau phất khi bước
    s.line(6, 16 + y, 10, 16 + y, C["indigo_dk"])
    hx = 8 if step == 0 else (10 if step > 0 else 6)        # tay vung ngược chân trước
    s.line(8, 12 + y, hx, 14 + y, C["indigo_dk"]); s.px(hx, 15 + y, C["skin"])
    # đầu nghiêng: tóc dài sau gáy, khăn quấn, nút + đuôi sau đầu, mũi nhô
    s.circle(8, 6 + y, 4, C["skin"], fill=True)
    s.rect(5, 2 + y, 10, 3 + y, C["hair"]); s.rect(4, 5 + y, 6, 10 + y, C["hair"])
    s.px(11, 5 + y, C["hair"])                              # mái trước trán
    checker(4, 12, 3 + y, 4 + y)
    s.px(3, 4 + y, C["cream"]); s.px(2, 5 + y + (step != 0), C["hair"]); s.px(2, 6 + y + (step != 0), C["cream"])
    s.rect(10, 6 + y, 10, 7 + y, C["hair"])                 # mắt
    s.px(13, 7 + y, C["skin"])                              # mũi
    s.px(11, 8 + y, C["dawn"]); s.px(8, 10 + y, C["skin_dk"])
    s.outline(C["ink"], where="outside")


first = True
for name, fn in (("down", lambda i: front(STEP[i], BOB[i])),
                 ("carry", lambda i: front(STEP[i], BOB[i], carry=True)),
                 ("side", lambda i: side(STEP[i], BOB[i]))):
    start = s.n_frames + (0 if first else 1)
    for i in range(4):
        if not first: s.add_frame(copy=False)
        first = False
        fn(i)
    s.tag(name, start, start + 3)
s.set_duration(140, frames="all")

if __name__ == "__main__":
    from PIL import Image
    s.preview("preview.png", scale=10, bg=C["silt"], cols=4)
    s.save_silhouette("silhouette.png", frame=1)
    s.stats()
    s.save_png("ut_sen_quan_1x.png", frame=1)
    s.save_spritesheet("ut_sen_quan_sheet.png", layout="row", scale=1)
    for tag in ("down", "carry", "side"):
        s.save_gif(f"ut_sen_{tag}.gif", scale=6, tag=tag, bg="#c79a63")
    # Cỡ thật trên sàn nhà bè (Pyxel 256x144, ~16 px/m): khung 1 mỗi tag + bản lật trái
    scr = Sprite(256, 144, palette=list(C.values()))
    scr.rect(0, 0, 255, 143, C["hair"])
    scr.rect(16, 8, 239, 135, "#c79a63")
    for yy in range(14, 136, 8): scr.line(16, yy, 239, yy, C["mud"])
    scr.save_png("_bg.png")
    bg = Image.open("_bg.png").convert("RGBA"); os.remove("_bg.png")
    for i, (fr, x, flip) in enumerate([(1, 60, False), (5, 100, False), (9, 140, False), (11, 180, True)]):
        s.save_png("_f.png", frame=fr)
        im = Image.open("_f.png").convert("RGBA")
        if flip: im = im.transpose(Image.FLIP_LEFT_RIGHT)
        bg.alpha_composite(im, (x, 60))
    os.remove("_f.png")
    bg.resize((256 * 4, 144 * 4), Image.NEAREST).save("in_game_4x.png")
