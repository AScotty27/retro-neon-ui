"""Check that every PNG (and every PNG inside an .ico) in the repo carries pixel data only.

    python tests/check_png_chunks.py
    python tests/check_png_chunks.py --strip <file.png> [...]   rewrite PNGs keeping only the allowed chunks

Allowed chunks: IHDR, PLTE, tRNS, IDAT, IEND. Anything else (tEXt, iTXt, zTXt, eXIf, iCCP, tIME, pHYs ...) can carry
generator prompts, file paths, user names or timestamps and fails the check. A planted control file with a tEXt chunk
is checked first; if the checker does not flag it, the whole run fails. Standard library only.
"""
import struct
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND"}
SIGNATURE = b"\x89PNG\r\n\x1a\n"
SKIP_DIRS = {"node_modules", "bin", "obj", "out", ".git", "work", "output"}


def chunks(data, start=0):
    """Chunk types of the PNG starting at data[start] (which must be the signature)."""
    pos = start + len(SIGNATURE)
    found = []
    while pos + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        found.append(kind)
        pos += 12 + length
        if kind == b"IEND":
            break
    return found


def extra_chunks(path):
    data = path.read_bytes()
    starts = [0] if path.suffix.lower() == ".png" else []
    if path.suffix.lower() == ".ico":
        i = data.find(SIGNATURE)
        while i != -1:
            starts.append(i)
            i = data.find(SIGNATURE, i + 1)
    if path.suffix.lower() == ".png" and not data.startswith(SIGNATURE):
        return ["not a PNG"]
    bad = []
    for s in starts:
        bad += [k.decode("latin-1") for k in chunks(data, s) if k not in ALLOWED]
    return bad


def strip(path):
    """Rewrite a PNG in place with only the allowed chunks (pixels untouched). Returns the dropped chunk types."""
    data = path.read_bytes()
    if not data.startswith(SIGNATURE):
        raise SystemExit(f"FAIL: not a PNG: {path}")
    out, dropped, pos = [SIGNATURE], [], len(SIGNATURE)
    while pos + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        whole = data[pos:pos + 12 + length]
        (out if kind in ALLOWED else dropped).append(whole if kind in ALLOWED else kind.decode("latin-1"))
        pos += 12 + length
        if kind == b"IEND":
            break
    path.write_bytes(b"".join(out))
    return dropped


def png_with_text():
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    idat = zlib.compress(b"\x00\x00")
    return SIGNATURE + chunk(b"IHDR", ihdr) + chunk(b"tEXt", b"Comment\x00planted") + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def main():
    if "--strip" in sys.argv:
        for name in sys.argv[sys.argv.index("--strip") + 1:]:
            print(f"stripped {name}: {', '.join(strip(Path(name))) or 'nothing to drop'}")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        control = Path(tmp) / "control.png"
        control.write_bytes(png_with_text())
        if extra_chunks(control) != ["tEXt"]:
            print("FAIL  control: the planted tEXt chunk was not flagged; the checker is broken")
            return 1
    print("PASS  control: planted tEXt chunk flagged")

    failures, count = 0, 0
    for path in sorted(ROOT.rglob("*")):
        if path.suffix.lower() not in (".png", ".ico") or SKIP_DIRS & set(path.relative_to(ROOT).parts):
            continue
        count += 1
        bad = extra_chunks(path)
        if bad:
            failures += 1
            print(f"FAIL  {path.relative_to(ROOT).as_posix()}: {', '.join(bad)}")
    print(f"{count} image files checked")
    if count == 0:
        print("FAIL  no images found")
        return 1
    print("ALL PASS" if not failures else f"{failures} FAILURE(S)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
