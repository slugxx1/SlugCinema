import os
import re
from pathlib import Path

INPUT_DIR = Path("frame_lua")
OUTPUT_DIR = Path("chunks_test")
CHUNK_SIZE = 24

def natural_key(path):
    parts = re.split(r"(\d+)", path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(INPUT_DIR.glob("frame_*.lua"), key=natural_key)
    if not files:
        print(f"No frame lua files found in {INPUT_DIR}")
        return

    chunk_index = 1
    for i in range(0, len(files), CHUNK_SIZE):
        batch = files[i:i+CHUNK_SIZE]
        out_path = OUTPUT_DIR / f"chunk_{chunk_index:03d}.lua"

        with open(out_path, "w", encoding="utf-8", newline="\n") as out:
            out.write("return {\n")
            for f in batch:
                text = f.read_text(encoding="utf-8").strip()
                if text.startswith("return"):
                    text = text[len("return"):].strip()
                out.write(f"  {text},\n")
            out.write("}\n")

        chunk_index += 1

    with open(OUTPUT_DIR / "chunks.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write(str(chunk_index - 1))

    print("done")

if __name__ == "__main__":
    main()
