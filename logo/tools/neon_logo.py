"""Neon redesign of a cartoon logo (the reference bird: conductor cap, plain maroon can), traced from the original.

    python logo/tools/neon_logo.py [--input logo/reference/original-bird.png] [--work logo/tools/work] [--debug]

Pipeline: split the cartoon into parts by colour (ink, cap, gold trim, visor, body, beak and feet, mouth, can,
pupils), thin the black ink lines to centre lines and redraw them as even neon tubes coloured by the part they
outline, tint or fill the parts, then add bloom, scanlines and a slight RGB split. Two concepts:
  A "sign"  = glowing tubes on dark tinted parts (a neon sign)         -> the "inverted" set,
  B "ident" = flat bright parts with a glowing rim (an 80s TV ident)  -> the "normal" set.
Each is written on black (square) and on transparency into the work folder; render_lockups.py and
export_brand.py take it from there.

Adapting it to another logo: segment() is tuned to the reference bird's colours (a thick black outline closed
around the figure, a big blue cap, yellow trim, a maroon can). Run with --debug, look at work/debug-parts.png
(one flat colour per part, centre lines magenta), and adjust the thresholds and the TUBE / PRIORITY tables.
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.morphology import disk, remove_small_objects, skeletonize

from common import REFERENCE, WORK, save_png

BG, INK, CAP, GOLD, VISOR, BODY, WARM, MOUTH, CAN, PUPIL = range(10)
NAMES = ["bg", "ink", "cap", "gold", "visor", "body", "warm", "mouth", "can", "pupil"]
DEBUG_COLORS = np.array([
    [0, 0, 0], [255, 255, 255], [40, 80, 255], [255, 220, 0], [90, 90, 90],
    [200, 200, 220], [255, 140, 0], [255, 80, 120], [180, 0, 40], [0, 255, 200]], dtype=np.uint8)


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


# Neon tube colours per part (the kit's palette).
TUBE = {
    BODY: hexrgb("#dff4ff"), CAP: hexrgb("#5b6cff"), GOLD: hexrgb("#ffd60a"), VISOR: hexrgb("#a63dff"),
    WARM: hexrgb("#ff8c1a"), MOUTH: hexrgb("#ff2e9a"), CAN: hexrgb("#ff3b4e"), PUPIL: hexrgb("#dff4ff"),
}
# Which part's colour an ink line takes when it borders several (higher wins).
PRIORITY = [BODY, VISOR, MOUTH, WARM, GOLD, CAP, CAN]


def load(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32)


def segment(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    sat = rgb.max(-1) - rgb.min(-1)

    ink = (lum < 45) & (sat < 40)
    # The black outline is closed around the figure, so filling its holes gives the silhouette.
    sil = ndi.binary_fill_holes(ndi.binary_dilation(ink, disk(2)))
    sil = remove_small_objects(sil, max_size=5000)
    ink &= sil
    inside = sil & ~ink

    label = np.full(rgb.shape[:2], BG, np.uint8)
    label[inside] = BODY
    label[inside & (sat < 30) & (lum >= 45) & (lum < 130)] = VISOR
    label[inside & (r > g + 50) & (r > b + 35) & (lum < 110)] = CAN
    label[inside & (r > g + 50) & (lum >= 110)] = MOUTH
    yellow = inside & (r > 200) & (g > 110) & (b < 140) & (g - b > 80)
    # The cap is the big blue area; small blue bits are eye reflections and stay body.
    blue = inside & (b > r + 35) & (b > g + 20)
    blue_comps, n_blue = ndi.label(blue)
    sizes = ndi.sum(blue, blue_comps, range(1, n_blue + 1))
    for i, size in enumerate(sizes, start=1):
        if size >= 2000:
            label[blue_comps == i] = CAP
    # Gold trim and the beak/feet share a colour; the trim is whatever yellow touches the cap.
    comps, n = ndi.label(yellow)
    near_cap = ndi.binary_dilation(label == CAP, disk(25))
    touching = set(np.unique(comps[near_cap & yellow])) - {0}
    for i in range(1, n + 1):
        label[comps == i] = GOLD if i in touching else WARM

    # Pupils are solid ink blobs, far thicker than any line: keep them as filled shapes.
    depth = ndi.distance_transform_edt(ink)
    solid = ndi.binary_dilation(depth > 9, disk(10)) & ink
    solid = ndi.binary_fill_holes(solid)
    label[ink] = INK
    label[solid & sil] = PUPIL
    return label, sil, ink & ~solid


def tube_colours(label, skel):
    """Colour each centre-line pixel by the highest-priority part within reach of it."""
    col = np.zeros(skel.shape + (3,), np.float32)
    col[skel] = TUBE[BODY]
    for part in PRIORITY:
        reach = ndi.binary_dilation(label == part, disk(10))
        col[skel & reach] = TUBE[part]
    return col


def draw_tubes(skel, col, half_width):
    """Anti-aliased tubes of even width along the centre lines, with a white-hot core."""
    dist, (iy, ix) = ndi.distance_transform_edt(~skel, return_indices=True)
    colour = col[iy, ix]
    body = np.clip(half_width + 0.5 - dist, 0, 1)[..., None]
    hot = np.clip(half_width * 0.45 + 0.5 - dist, 0, 1)[..., None]
    return colour * body * 0.95 + (1.0 - colour) * hot * 0.55


def bloom(emissive, strength=1.0):
    out = np.zeros_like(emissive)
    for sigma, weight in ((3, 0.55), (9, 0.45), (24, 0.35), (60, 0.25)):
        for c in range(3):
            out[..., c] += ndi.gaussian_filter(emissive[..., c], sigma) * weight
    return out * strength


def finish(img, split=2, scan=0.16):
    """Scanlines and a slight RGB split, the CRT part of the look."""
    img = img.copy()
    img[::3, :, :] *= 1.0 - scan
    if split:
        img[..., 0] = np.roll(img[..., 0], -split, axis=1)
        img[..., 2] = np.roll(img[..., 2], split, axis=1)
    return np.clip(img, 0, 1)


def concept_sign(label, sil, skel_ink):
    col = tube_colours(label, skel_ink)
    emissive = draw_tubes(skel_ink, col, half_width=4.2)
    pupils = (label == PUPIL)[..., None]
    emissive = np.maximum(emissive, pupils * TUBE[PUPIL])
    # Dark tinted parts behind the tubes (the acrylic a sign is mounted on).
    tint = np.zeros_like(emissive)
    for part, amount in ((BODY, 0.14), (CAP, 0.28), (GOLD, 0.22), (VISOR, 0.20), (WARM, 0.25), (MOUTH, 0.30), (CAN, 0.34)):
        tint[label == part] = TUBE[part] * amount
    return finish(tint + emissive + bloom(emissive, 0.9))


def concept_ident(label, sil, skel_ink, rgb):
    flat = {
        BODY: hexrgb("#e4e2ff"), CAP: hexrgb("#3d4dff"), GOLD: hexrgb("#ffd60a"), VISOR: hexrgb("#2a1f55"),
        WARM: hexrgb("#ff8c1a"), MOUTH: hexrgb("#ff2e9a"), CAN: hexrgb("#d0002f"), PUPIL: hexrgb("#120a2a"),
    }
    base = np.zeros(label.shape + (3,), np.float32)
    for part, colour in flat.items():
        base[label == part] = colour
    # Keep the cartoon's own shading inside each part, flattened to two bands (posterised).
    lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) / 255.0
    local = ndi.uniform_filter(lum, 41)
    shade = np.where(lum < local - 0.04, 0.78, 1.0)[..., None]
    base = base * np.where((label != INK)[..., None], shade, 1.0)
    base[label == INK] = hexrgb("#0b0820")
    # A glowing magenta-to-cyan rim just outside the silhouette.
    ring = ndi.binary_dilation(sil, disk(9)) & ~ndi.binary_dilation(sil, disk(4))
    yy = np.linspace(0, 1, label.shape[0])[:, None, None]
    rim_colour = hexrgb("#ff2e9a") * (1 - yy) + hexrgb("#2de2ff") * yy
    emissive = ring[..., None] * rim_colour + base * 0.22
    return finish(base * sil[..., None] + ring[..., None] * rim_colour + bloom(emissive, 1.0), split=3)


def crop_square(img, sil, margin=0.09):
    ys, xs = np.nonzero(sil)
    cy, cx = (ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2
    half = max(ys.max() - ys.min(), xs.max() - xs.min()) / 2 * (1 + margin)
    y0, x0 = int(round(cy - half)), int(round(cx - half))
    size = int(round(half * 2))
    pad = size
    padded = np.pad(img, ((pad, pad), (pad, pad), (0, 0)))
    return padded[y0 + pad:y0 + pad + size, x0 + pad:x0 + pad + size]


def save(img, name, work):
    rgb8 = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
    save_png(Image.fromarray(rgb8), work / f"{name}-on-black.png")
    # Transparent copy: the light IS the image, so alpha follows the brightest channel.
    alpha = np.clip(img.max(-1), 0, 1)
    straight = np.where(alpha[..., None] > 1e-4, img / np.maximum(alpha[..., None], 1e-4), 0)
    rgba = np.dstack([np.clip(straight, 0, 1), alpha])
    save_png(Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA"), work / f"{name}-transparent.png")
    print(f"wrote {name}-on-black.png and {name}-transparent.png ({rgb8.shape[1]}x{rgb8.shape[0]})")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--input", type=Path, default=REFERENCE, help="the original cartoon logo (PNG)")
    parser.add_argument("--work", type=Path, default=WORK, help="folder for the concept PNGs")
    parser.add_argument("--debug", action="store_true", help="also write work/debug-parts.png")
    args = parser.parse_args()
    if not args.input.is_file():
        raise SystemExit(f"FAIL: input not found: {args.input}")
    args.work.mkdir(parents=True, exist_ok=True)

    rgb = load(args.input)
    label, sil, line_ink = segment(rgb)
    if not sil.any():
        raise SystemExit("FAIL: no closed outline found; this input needs segment() tuning (see the module notes)")
    skel = skeletonize(line_ink)
    skel = remove_small_objects(skel, max_size=12, connectivity=2)
    if args.debug:
        dbg = DEBUG_COLORS[label].copy()
        dbg[skel] = [255, 0, 255]
        save_png(Image.fromarray(dbg), args.work / "debug-parts.png")
        print("pixels per part:", {NAMES[i]: int((label == i).sum()) for i in range(len(NAMES))})
    save(crop_square(concept_sign(label, sil, skel), sil), "concept-a-sign", args.work)
    save(crop_square(concept_ident(label, sil, skel, rgb), sil), "concept-b-ident", args.work)


if __name__ == "__main__":
    main()
