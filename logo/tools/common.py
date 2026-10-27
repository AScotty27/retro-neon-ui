"""Shared helpers for the logo tools: repo paths and a PNG writer that keeps pixel data only."""
from pathlib import Path

from PIL import Image

TOOLS = Path(__file__).resolve().parent
LOGO = TOOLS.parent
REPO = LOGO.parent
REFERENCE = LOGO / "reference" / "original-bird.png"
WORK = TOOLS / "work"


def save_png(img, path):
    """Write a PNG from the pixel data alone: no text chunks, no colour profile, no timestamps, no dpi.

    Image metadata can carry generator prompts, file paths or user names, so every PNG these tools write goes
    through here. Rebuilding the image from its raw bytes drops whatever .info the source carried.
    """
    clean = Image.frombytes(img.mode, img.size, img.tobytes())
    clean.save(path, format="PNG", optimize=True)
