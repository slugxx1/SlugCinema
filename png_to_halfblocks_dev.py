import argparse
import math
import re
from pathlib import Path
from PIL import Image

# =========================================================
# ARGUMENTS
# =========================================================
parser = argparse.ArgumentParser(description="Convert PNG frames to ComputerCraft half-block Lua frames.")
parser.add_argument("--input", default="frames", help="Input folder containing PNG frames")
parser.add_argument("--output", default="frame_lua", help="Output folder for Lua frame files")
parser.add_argument("--mode", default="normal", choices=["normal", "dark"], help="Processing mode")
parser.add_argument("--width", type=int, default=0, help="Optional force width before conversion")
parser.add_argument("--height", type=int, default=0, help="Optional force height before conversion")
args = parser.parse_args()

INPUT_DIR = Path(args.input)
OUTPUT_DIR = Path(args.output)

# =========================================================
# COMPUTERCRAFT COLOR PALETTE
# hex digit matches blit color digit
# =========================================================
CC_PALETTE = {
    "0": (240, 240, 240),  # white
    "1": (242, 178, 51),   # orange
    "2": (229, 127, 216),  # magenta
    "3": (153, 178, 242),  # light blue
    "4": (222, 222, 108),  # yellow
    "5": (127, 204, 25),   # lime
    "6": (242, 178, 204),  # pink
    "7": (76, 76, 76),     # gray
    "8": (153, 153, 153),  # light gray
    "9": (76, 153, 178),   # cyan
    "a": (178, 102, 229),  # purple
    "b": (51, 102, 204),   # blue
    "c": (127, 102, 76),   # brown
    "d": (87, 166, 78),    # green
    "e": (204, 76, 76),    # red
    "f": (17, 17, 17),     # black
}

HALF_BLOCK = "\u2580"  # upper half block

# ordered dither matrix (4x4)
BAYER_4X4 = [
    [0,  8,  2, 10],
    [12, 4, 14,  6],
    [3, 11,  1,  9],
    [15, 7, 13,  5],
]

# =========================================================
# HELPERS
# =========================================================
def natural_key(path: Path):
    parts = re.split(r"(\d+)", path.name)
    out = []
    for p in parts:
        if p.isdigit():
            out.append(int(p))
        else:
            out.append(p.lower())
    return out

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def apply_mode(r, g, b, mode, x, y):
    # luminance
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b

    # mild ordered dithering to help gradients survive palette reduction
    d = BAYER_4X4[y % 4][x % 4]
    dither = (d - 7.5) * 1.6

    if mode == "dark":
        # lift shadows more aggressively
        if lum < 50:
            scale = 1.34
        elif lum < 90:
            scale = 1.22
        elif lum < 140:
            scale = 1.10
        else:
            scale = 1.02

        r = r * scale + 8 + dither
        g = g * scale + 8 + dither
        b = b * scale + 8 + dither

        # slight contrast bump around midpoint
        r = (r - 128) * 1.10 + 128
        g = (g - 128) * 1.10 + 128
        b = (b - 128) * 1.10 + 128

        # reduce purple/pink tendency a bit in low-light skin regions
        if r > g and b > g and lum < 150:
            b *= 0.92

    else:
        # normal mode, lighter touch
        if lum < 70:
            scale = 1.12
        elif lum < 120:
            scale = 1.06
        else:
            scale = 1.00

        r = r * scale + dither
        g = g * scale + dither
        b = b * scale + dither

    return (
        int(clamp(round(r), 0, 255)),
        int(clamp(round(g), 0, 255)),
        int(clamp(round(b), 0, 255)),
    )

def color_distance(c1, c2):
    # weighted RGB distance
    r1, g1, b1 = c1
    r2, g2, b2 = c2
    dr = r1 - r2
    dg = g1 - g2
    db = b1 - b2
    return (2 * dr * dr) + (4 * dg * dg) + (3 * db * db)

def nearest_cc_color(rgb):
    best_key = None
    best_dist = None

    r, g, b = rgb
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b

    for key, pal_rgb in CC_PALETTE.items():
        dist = color_distance(rgb, pal_rgb)

        # discourage pink/magenta a bit in dark scenes
        if key in ("2", "6") and lum < 160:
            dist *= 1.18

        # encourage grays for near-neutral colors
        if abs(r - g) < 14 and abs(g - b) < 14:
            if key in ("7", "8", "0", "f"):
                dist *= 0.88

        # encourage red/orange warmth over pink for warm areas
        if r > g and g > b:
            if key in ("1", "c", "e"):
                dist *= 0.90

        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_key = key

    return best_key

def lua_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')

def save_lua_frame(path: Path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("return {\n")
        for text, fg, bg in rows:
            f.write(f'  {{"{lua_escape(text)}","{fg}","{bg}"}},\n')
        f.write("}\n")

def convert_image_to_halfblocks(img: Image.Image, mode: str):
    img = img.convert("RGB")
    width, height = img.size

    # height should be even for half-block pairing
    if height % 2 != 0:
        img = img.crop((0, 0, width, height - 1))
        width, height = img.size

    px = img.load()
    rows = []

    for y in range(0, height, 2):
        text_parts = []
        fg_parts = []
        bg_parts = []

        for x in range(width):
            top = apply_mode(*px[x, y], mode, x, y)
            bottom = apply_mode(*px[x, y + 1], mode, x, y + 1)

            top_key = nearest_cc_color(top)
            bottom_key = nearest_cc_color(bottom)

            text_parts.append(HALF_BLOCK)
            fg_parts.append(top_key)
            bg_parts.append(bottom_key)

        rows.append((
            "".join(text_parts),
            "".join(fg_parts),
            "".join(bg_parts),
        ))

    return rows

# =========================================================
# MAIN
# =========================================================
def main():
    if not INPUT_DIR.exists():
        print(f"Input folder not found: {INPUT_DIR}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(INPUT_DIR.glob("*.png"), key=natural_key)
    if not files:
        print(f"No PNG files found in {INPUT_DIR}")
        return

    for i, file_path in enumerate(files, start=1):
        img = Image.open(file_path).convert("RGB")

        if args.width > 0 and args.height > 0:
            img = img.resize((args.width, args.height), Image.Resampling.LANCZOS)

        rows = convert_image_to_halfblocks(img, args.mode)
        out_path = OUTPUT_DIR / f"frame_{i:04d}.lua"
        save_lua_frame(out_path, rows)

        if i % 25 == 0:
            print(f"Wrote {i}/{len(files)}")

    print("done")

if __name__ == "__main__":
    main()
