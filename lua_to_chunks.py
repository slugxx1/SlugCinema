from pathlib import Path
import re

INPUT_DIR = Path("frame_lua")
OUTPUT_DIR = Path("chunks")
CHUNK_SIZE = 24  # frames per chunk

def natural_key(p: Path):
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", p.stem)]

def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # clean old chunk files
    for f in OUTPUT_DIR.glob("chunk_*.lua"):
        f.unlink()

    files = sorted(INPUT_DIR.glob("frame_*.lua"), key=natural_key)
    total_frames = len(files)

    if total_frames == 0:
        print("No frame lua files found in frame_lua")
        return

    chunk_count = 0

    for i in range(0, total_frames, CHUNK_SIZE):
        group = files[i:i + CHUNK_SIZE]
        chunk_count += 1
        out_path = OUTPUT_DIR / f"chunk_{chunk_count:03d}.lua"

        with open(out_path, "w", encoding="utf-8", newline="\n") as out:
            out.write("return {\n")
            for frame_file in group:
                with open(frame_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()

                # strip leading 'return' so it becomes nested table data
                if content.startswith("return"):
                    content = content[len("return"):].strip()

                out.write(content)
                out.write(",\n")
            out.write("}\n")

    with open("count.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write(str(total_frames))

    with open("chunks.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write(str(chunk_count))

    print(f"packed: {total_frames} frames into {chunk_count} chunks")

if __name__ == "__main__":
    main()
