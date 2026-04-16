from pathlib import Path
import re
from PIL import Image

INPUT_DIR = Path("frames")
OUTPUT_DIR = Path("frame_lua")
PREVIEW_DIR = Path("preview_full")
OUTPUT_PREFIX = "frame_"

HALF_BLOCK = "\u2580"
HEX = "0123456789abcdef"

# CC / CC:Tweaked palette
CC = [
    (240, 240, 240),  # 0 white
    (242, 178, 51),   # 1 orange
    (229, 127, 216),  # 2 magenta
    (153, 178, 242),  # 3 light blue
    (222, 222, 108),  # 4 yellow
    (127, 204, 25),   # 5 lime
    (242, 178, 204),  # 6 pink
    (76, 76, 76),     # 7 gray
    (153, 153, 153),  # 8 light gray
    (76, 153, 178),   # 9 cyan
    (178, 102, 229),  # a purple
    (51, 102, 204),   # b blue
    (127, 102, 76),   # c brown
    (87, 166, 78),    # d green
    (204, 76, 76),    # e red
    (17, 17, 17),     # f black
]

nearest_cache = {}

def natural_key(p: Path):
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", p.stem)]

def dist(a, b):
    return (
        (a[0] - b[0]) ** 2 +
        (a[1] - b[1]) ** 2 +
        (a[2] - b[2]) ** 2
    )

def nearest(rgb):
    cached = nearest_cache.get(rgb)
    if cached is not None:
        return cached

    best_i = 0
    best_d = float("inf")

    for i, c in enumerate(CC):
        d = dist(rgb, c)

        # 🚫 eliminate magenta & pink completely
        if i == 2:   # magenta
            d += 100000
        elif i == 6: # pink
            d += 100000

        # ✅ slightly favor orange instead
        if i == 1:   # orange
            d -= 300

        if d < best_d:
            best_d = d
            best_i = i

    nearest_cache[rgb] = best_i
    return best_i

def quantize(img: Image.Image):
    px = img.load()
    w, h = img.size
    out = []

    for y in range(h):
        row = []
        for x in range(w):
            row.append(nearest(px[x, y]))
        out.append(row)

    return out

def save_preview(q, path: Path):
    h = len(q)
    w = len(q[0]) if h else 0
    img = Image.new("RGB", (w, h))
    px = img.load()

    for y in range(h):
        for x in range(w):
            px[x, y] = CC[q[y][x]]

    img.save(path)

def to_halfblocks(q):
    if len(q) % 2:
        q.append(q[-1][:])

    lines = []
    for y in range(0, len(q), 2):
        top = q[y]
        bot = q[y + 1]

        t = ""
        f = ""
        b = ""

        for x in range(len(top)):
            t += HALF_BLOCK
            f += HEX[top[x]]
            b += HEX[bot[x]]

        lines.append((t, f, b))

    return lines

def write_lua(path: Path, lines):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("return {\n")
        for t, fg, bg in lines:
            # FORCE raw UTF-8, no escaping at all
            f.write('{"%s","%s","%s"},\n' % (t, fg, bg))
        f.write("}\n")

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    PREVIEW_DIR.mkdir(exist_ok=True)

    for f in OUTPUT_DIR.glob("*.lua"):
        f.unlink()
    for f in PREVIEW_DIR.glob("*.png"):
        f.unlink()

    files = sorted(INPUT_DIR.glob("*.png"), key=natural_key)

    nearest_cache.clear()

    for i, f in enumerate(files, 1):
        img = Image.open(f).convert("RGB")
        q = quantize(img)

        write_lua(OUTPUT_DIR / f"{OUTPUT_PREFIX}{i:04d}.lua", to_halfblocks(q))
        save_preview(q, PREVIEW_DIR / f"{OUTPUT_PREFIX}{i:04d}.png")

        if i % 50 == 0:
            print(i)

    print("done")

if __name__ == "__main__":
    main()
