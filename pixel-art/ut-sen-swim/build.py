"""Út Sen lặn (nhìn ngang, quay phải) — 28x16, 4 khung đạp chân. Chạy: python build.py

Quy ước màu: CHỈ viền ngoài dùng "ink". Tóc và ô đen khăn rằn dùng "hair".
Nhờ vậy game đổi riêng màu viền bằng pyxel.pal(INK, CREAM) khi lặn sâu mà không đổi tóc/khăn.
"""
import os, sys
sys.path.insert(0, os.path.expanduser("~/.claude/skills/pixel-art-studio/scripts"))
from pixelstudio import Sprite

# Bảng màu chung của game: 16 màu, nạp thẳng vào pyxel.colors (thứ tự = chỉ số màu Pyxel)
GAME = {
    "ink": "#1a1410", "hair": "#3a3120", "mud": "#6b5a38", "silt": "#a8915c",
    "dawn": "#f4b9a0", "cream": "#fbe3c4", "indigo_dk": "#2b3a5e", "indigo": "#45598a",
    "glass": "#9fd3e0", "skin": "#e9b88f", "skin_dk": "#b9785a", "wood_dk": "#5e3b1f",
    "bamboo": "#a07a3c", "palm": "#4f7a3a", "lantern": "#ffcf5a", "red": "#e5564b",
}
C = GAME
W, H = 28, 16  # 16: chân dưới khi đạp mạnh + nhấp nhô vẫn còn chỗ cho viền
s = Sprite(W, H, palette=list(GAME.values()))


def draw(kick, flap, bob):
    """kick: chân mở (0..2); flap: đuôi khăn/vạt áo phất (0/1); bob: thân nhấp nhô (0/1)."""
    y = bob
    # chân: quần chàm sẫm, hai chân tách hình chữ V
    s.line(8, 8 + y, 3, 7 - kick + y, C["indigo_dk"])
    s.line(8, 10 + y, 3, 11 + kick + y, C["indigo_dk"])
    s.line(7, 9 + y, 4, 8 - kick + y, C["indigo_dk"])
    s.px(2, 7 - kick + y, C["skin"]); s.px(2, 11 + kick + y, C["skin"])
    # thân áo bà ba thon từ vai về hông + vạt áo xẻ tà bay ra sau
    s.rect(8, 8 + y, 10, 10 + y, C["indigo"])
    s.rect(11, 7 + y, 14, 10 + y, C["indigo"])
    s.rect(15, 6 + y, 17, 10 + y, C["indigo"])
    s.line(9, 10 + y, 17, 10 + y, C["indigo_dk"])
    s.line(9, 11 + y, 6 - flap, 11 + flap + y, C["indigo"])        # vạt áo sau
    s.px(16, 8 + y, C["cream"]); s.px(16, 10 + y, C["cream"])      # hàng nút
    # giỏ lưới bo tròn, đan ô (tre sáng / tre sẫm), miệng giỏ viền tre
    s.line(11, 3 + y, 13, 3 + y, C["bamboo"])
    for gy, (x0, x1) in zip((4, 5, 6), ((10, 14), (10, 14), (11, 13))):
        for gx in range(x0, x1 + 1):
            s.px(gx, gy + y, C["wood_dk"] if (gx + gy) % 2 else C["bamboo"])
    s.line(14, 6 + y, 16, 8 + y, C["wood_dk"])                      # quai giỏ
    # đầu
    s.circle(21, 6 + y, 3, C["skin"], fill=True)
    s.rect(18, 3 + y, 22, 3 + y, C["hair"])
    s.rect(18, 4 + y, 19, 7 + y, C["hair"])
    s.px(20, 9 + y, C["skin_dk"]); s.px(21, 9 + y, C["skin_dk"])
    # khăn rằn: dải ô ngang trán + nút sau gáy + đuôi bay
    for x in range(18, 24):
        s.px(x, 4 + y, C["cream"] if x % 2 else C["hair"])
    s.px(17, 4 + y, C["cream"]); s.px(17, 5 + y, C["hair"])
    for i, x in enumerate((16, 15, 14)):
        ty = 3 - flap + y
        s.px(x, ty, C["cream"] if i % 2 == 0 else C["hair"])
        s.px(x, ty + 1, C["hair"] if i % 2 == 0 else C["cream"])
    # kính lặn khung tre
    s.rect(22, 5 + y, 23, 6 + y, C["glass"])
    s.px(24, 5 + y, C["bamboo"]); s.px(24, 6 + y, C["bamboo"])
    s.line(19, 5 + y, 21, 5 + y, C["bamboo"])
    s.px(23, 6 + y, C["hair"])
    # tay vươn trước dưới cằm
    s.line(17, 9 + y, 19, 10 + y, C["indigo"])
    s.line(20, 10 + y, 25, 9 - (kick == 2) + y, C["skin"])
    s.px(26, 9 - (kick == 2) + y, C["skin"])
    s.outline(C["ink"], where="outside")


frames = [(0, 0, 0), (1, 1, 0), (2, 1, 1), (1, 0, 1)]
for i, (k, f, b) in enumerate(frames):
    if i: s.add_frame(copy=False)   # frame index is 1-based; add_frame selects the new frame
    draw(k, f, b)
s.set_duration(120, frames="all")
s.tag("swim", 1, 4)

if __name__ == "__main__":
    from PIL import Image
    s.preview("preview.png", scale=10, bg=C["silt"])
    s.save_silhouette("silhouette.png", frame=1)
    s.stats()
    s.save_png("ut_sen_swim_1x.png", frame=1)
    s.save_spritesheet("ut_sen_swim_sheet.png", layout="row", scale=1)
    s.save_gif("ut_sen_swim.gif", scale=6, tag="swim", bg=C["silt"])

    # Cỡ thật trên màn hình Pyxel 256x144; tầng sâu dùng viền kem (mô phỏng pyxel.pal(ink, cream))
    scr = Sprite(256, 144, palette=list(GAME.values()))
    scr.rect(0, 0, 255, 17, C["dawn"]); scr.rect(0, 14, 255, 17, C["palm"])
    scr.rect(0, 18, 255, 60, C["silt"]); scr.rect(0, 61, 255, 110, C["mud"])
    scr.rect(0, 111, 255, 143, C["hair"]); scr.line(0, 18, 255, 18, C["cream"])
    scr.save_png("_bg.png")
    bg = Image.open("_bg.png").convert("RGBA"); os.remove("_bg.png")
    sheet = Image.open("ut_sen_swim_sheet.png").convert("RGBA")
    spr = sheet.crop((0, H, W, 2 * H))  # sheet là lưới 2x2: khung 3 ở hàng 2, cột 1
    ink = tuple(int(C["ink"][i:i + 2], 16) for i in (1, 3, 5)) + (255,)
    cream = tuple(int(C["cream"][i:i + 2], 16) for i in (1, 3, 5)) + (255,)
    deep = spr.copy(); px = deep.load()
    for yy in range(deep.height):
        for xx in range(deep.width):
            if px[xx, yy] == ink: px[xx, yy] = cream
    for img, (x, yy) in [(spr, (40, 30)), (spr, (150, 75)), (deep, (200, 120)), (spr, (90, 122))]:
        bg.alpha_composite(img, (x, yy))
    bg.resize((256 * 4, 144 * 4), Image.NEAREST).save("in_game_4x.png")
