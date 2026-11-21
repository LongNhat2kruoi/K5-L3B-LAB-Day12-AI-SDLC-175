"""Đóng gói asset cho game Pyxel từ nguồn vẽ trong pixel-art/. Chạy lại khi sửa sprite:

    python play/build_assets.py

Xuất vào play/assets/: sprite sheet nền màu khóa (colkey), frames.json (tọa độ khung + bảng màu), font + giấy phép.
"""
import json, os, shutil, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "pixel-art")
OUT = os.path.join(ROOT, "play", "assets")
sys.path.insert(0, os.path.join(ART, "ut-sen-swim"))
from build import GAME  # bảng 16 màu chung  # noqa: E402

KEY = GAME["lantern"]  # màu 14 không xuất hiện trong sprite nhân vật -> dùng làm màu trong suốt


def keyed(src, dst):
    im = Image.open(src).convert("RGBA")
    bg = Image.new("RGBA", im.size, KEY)
    bg.alpha_composite(im)
    bg.convert("RGB").save(dst)


def frames(path):
    d = json.load(open(path))
    fr = d["frames"].values() if isinstance(d["frames"], dict) else d["frames"]
    return [[f["frame"][k] for k in ("x", "y", "w", "h")] for f in fr]


os.makedirs(OUT, exist_ok=True)
keyed(os.path.join(ART, "ut-sen-swim", "ut_sen_swim_sheet.png"), os.path.join(OUT, "ut_sen_swim.png"))
keyed(os.path.join(ART, "ut-sen-quan", "ut_sen_quan_sheet.png"), os.path.join(OUT, "ut_sen_quan.png"))
meta = {
    "colors": [int(c[1:], 16) for c in GAME.values()],
    "names": list(GAME.keys()),
    "swim": frames(os.path.join(ART, "ut-sen-swim", "ut_sen_swim_sheet.json")),
    "quan": frames(os.path.join(ART, "ut-sen-quan", "ut_sen_quan_sheet.json")),
}
json.dump(meta, open(os.path.join(OUT, "frames.json"), "w"), indent=1)
font_dir = os.path.join(ART, "pyxel-spike", "fonts")
shutil.copy(os.path.join(font_dir, "ark-pixel-10px-proportional-latin.bdf"), OUT)
shutil.copy(os.path.join(font_dir, "OFL.txt"), os.path.join(OUT, "OFL-ark-pixel-font.txt"))
print("assets ->", OUT, sorted(os.listdir(OUT)))
