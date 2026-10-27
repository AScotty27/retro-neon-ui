"""Export the logo set from the work folder: normal + inverted (bird, badges 1024 to 16, discs) and web icons.

    python logo/tools/export_brand.py [--work logo/tools/work] [--out logo] [--with-lockup]

Run neon_logo.py and render_lockups.py first (this reads their work folder). "normal" = concept B (TV ident, white
bird, reads down to 32 px, the everyday logo); "inverted" = concept A (neon sign, best at 128 px and up).
Writes <out>/normal/, <out>/inverted/ and <out>/web/ (favicon.ico, favicon-64.png, apple-touch-icon.png).
--with-lockup also writes full-logo-*.png (stripes + badge + wordmark from render_lockups.py --name/--tag) and
web/og-card.png (1200x630 link preview). Only *.png and *.ico files directly in those three folders are replaced;
nothing else under --out is touched.
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from common import LOGO, WORK, save_png

VARIANTS = {"normal": "b", "inverted": "a"}
SOURCES = {"normal": "concept-b-ident", "inverted": "concept-a-sign"}
BADGE_SIZES = (512, 256, 128, 64, 48, 32, 16)


def on_black(img):
    black = Image.new("RGBA", img.size, (0, 0, 0, 255))
    return Image.alpha_composite(black, img.convert("RGBA")).convert("RGB")


def disc(bird, size=1024):
    """The bird on the dark scanlined disc, full bleed (no ring), transparent corners: for round avatar slots."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    r = np.hypot(xx - size / 2, (yy - size * 0.38)) / (size * 0.62)
    inner, outer = np.array([0x1d, 0x14, 0x40], np.float32), np.array([0x05, 0x04, 0x0b], np.float32)
    rgb = inner + (outer - inner) * np.clip(r, 0, 1)[..., None]
    rgb[(np.arange(size) % 5 < 2)] *= 0.78
    bg = Image.fromarray(rgb.astype(np.uint8)).convert("RGBA")
    scale = int(size * 0.86)
    b = bird.convert("RGBA").resize((scale, scale), Image.LANCZOS)
    bg.alpha_composite(b, ((size - scale) // 2, int(size * 0.52 - scale / 2)))
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    bg.putalpha(mask.resize((size, size), Image.LANCZOS))
    return bg


def og_card(lockup):
    """1200x630 link-preview card: the full logo on black with a soft glow and scanlines."""
    w, h = 1200, 630
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    glow = np.exp(-(((xx - w / 2) / 520) ** 2 + ((yy - h * 0.55) / 260) ** 2))
    rgb = np.zeros((h, w, 3), np.float32) + np.array([5, 4, 11], np.float32)
    rgb += glow[..., None] * np.array([60, 18, 90], np.float32)
    rgb[(np.arange(h) % 4 < 1)] *= 0.8
    card = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGBA")
    target_w = 1100
    logo = lockup.convert("RGBA")
    logo = logo.resize((target_w, round(logo.height * target_w / logo.width)), Image.LANCZOS)
    card.alpha_composite(logo, ((w - logo.width) // 2, (h - logo.height) // 2))
    return card.convert("RGB")


def clear(folder):
    """Remove only the image files this tool writes, so stale sizes cannot linger; never recurse."""
    folder.mkdir(parents=True, exist_ok=True)
    for path in folder.iterdir():
        if path.is_file() and path.suffix.lower() in (".png", ".ico"):
            path.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--work", type=Path, default=WORK, help="folder holding the neon_logo/render_lockups output")
    parser.add_argument("--out", type=Path, default=LOGO, help="where normal/, inverted/ and web/ go")
    parser.add_argument("--with-lockup", action="store_true", help="also write the full logos and the og card")
    args = parser.parse_args()
    work = args.work.resolve()

    needed = [work / f"{SOURCES[n]}-{kind}.png" for n in VARIANTS for kind in ("transparent", "on-black")]
    needed += [work / f"badge-{letter}.png" for letter in VARIANTS.values()]
    if args.with_lockup:
        needed += [work / f"lockup-{letter}.png" for letter in VARIANTS.values()]
    missing = [p.name for p in needed if not p.is_file()]
    if missing:
        raise SystemExit(f"FAIL: run neon_logo.py and render_lockups.py first; missing {missing} in {work}")

    written = []
    for name, letter in VARIANTS.items():
        d = args.out / name
        clear(d)
        bird = Image.open(work / f"{SOURCES[name]}-transparent.png")
        badge = Image.open(work / f"badge-{letter}.png").convert("RGBA")
        files = {
            "bird-transparent.png": bird,
            "bird-on-black.png": Image.open(work / f"{SOURCES[name]}-on-black.png"),
            "badge-transparent-1024.png": badge,
            "badge-on-black-1024.png": on_black(badge),
            "disc-1024.png": disc(bird),
        }
        if args.with_lockup:
            lockup = Image.open(work / f"lockup-{letter}.png").convert("RGBA")
            files["full-logo-transparent.png"] = lockup
            files["full-logo-on-black.png"] = on_black(lockup)
        for size in BADGE_SIZES:
            files[f"badge-transparent-{size}.png"] = badge.resize((size, size), Image.LANCZOS)
        for size in (256, 128):
            files[f"disc-{size}.png"] = files["disc-1024.png"].resize((size, size), Image.LANCZOS)
        for fname, img in files.items():
            save_png(img, d / fname)
            written.append(d / fname)

    web = args.out / "web"
    clear(web)
    badge_n = Image.open(args.out / "normal" / "badge-transparent-1024.png")
    badge_n.save(web / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    save_png(badge_n.resize((64, 64), Image.LANCZOS), web / "favicon-64.png")
    save_png(on_black(badge_n).resize((180, 180), Image.LANCZOS), web / "apple-touch-icon.png")
    if args.with_lockup:
        save_png(og_card(Image.open(args.out / "normal" / "full-logo-transparent.png")), web / "og-card.png")
    written += sorted(p for p in web.iterdir() if p.suffix.lower() in (".png", ".ico"))

    for path in written:
        with Image.open(path) as img:
            print(f"{path.stat().st_size:>9,} B  {img.size[0]}x{img.size[1]}  {path.name}")
    print(f"{len(written)} files")


if __name__ == "__main__":
    main()
