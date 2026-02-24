# -*- coding: utf-8 -*-
"""
Generate a simple blue lock icon (64x64) using Pillow.

No external asset files needed.
"""

from __future__ import annotations

from PIL import Image, ImageDraw


def make_lock_icon(size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Colors
    blue = (40, 110, 255, 255)
    blue_dark = (25, 70, 190, 255)
    white = (255, 255, 255, 255)

    # Body
    body_w = int(size * 0.62)
    body_h = int(size * 0.46)
    body_x0 = (size - body_w) // 2
    body_y0 = int(size * 0.42)
    body_x1 = body_x0 + body_w
    body_y1 = body_y0 + body_h
    radius = int(size * 0.08)

    d.rounded_rectangle([body_x0, body_y0, body_x1, body_y1], radius=radius, fill=blue, outline=blue_dark, width=2)

    # Shackle (arc)
    sh_w = int(size * 0.50)
    sh_h = int(size * 0.52)
    sh_x0 = (size - sh_w) // 2
    sh_y0 = int(size * 0.10)
    sh_x1 = sh_x0 + sh_w
    sh_y1 = sh_y0 + sh_h

    # Outer arc
    d.arc([sh_x0, sh_y0, sh_x1, sh_y1], start=200, end=-20, fill=blue, width=int(size * 0.08))

    # Cutout / inner arc (fake thickness by drawing a smaller arc in transparent)
    inner_pad = int(size * 0.08)
    d.arc([sh_x0 + inner_pad, sh_y0 + inner_pad, sh_x1 - inner_pad, sh_y1 - inner_pad],
          start=200, end=-20, fill=(0, 0, 0, 0), width=int(size * 0.08))

    # Keyhole
    kh_cx = size // 2
    kh_cy = int(size * 0.64)
    kh_r = int(size * 0.06)
    d.ellipse([kh_cx - kh_r, kh_cy - kh_r, kh_cx + kh_r, kh_cy + kh_r], fill=white)
    stem_w = int(size * 0.06)
    stem_h = int(size * 0.10)
    d.rounded_rectangle([kh_cx - stem_w // 2, kh_cy, kh_cx + stem_w // 2, kh_cy + stem_h],
                        radius=stem_w // 2, fill=white)

    return img
