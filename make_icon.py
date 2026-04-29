"""生成 AppIcon.icns — 声波风格图标"""

import struct
import zlib
import math
import os


def make_png(size: int) -> bytes:
    img = [[(0, 0, 0, 0)] * size for _ in range(size)]
    s = size

    def set_px(x, y, color, alpha=255):
        if 0 <= x < s and 0 <= y < s:
            r, g, b = color
            img[y][x] = (r, g, b, alpha)

    def blend(x, y, color, t):
        if 0 <= x < s and 0 <= y < s:
            r, g, b = color
            pr, pg, pb, pa = img[y][x]
            a = int(t * 255)
            img[y][x] = (r, g, b, a)

    # ── Background: dark gradient circle ──────────────────────
    bg1 = (15, 20, 40)    # deep navy
    bg2 = (30, 60, 120)   # mid blue

    cx, cy = s / 2, s / 2
    R = s / 2
    for y in range(s):
        for x in range(s):
            dx, dy = x - cx, y - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > R:
                continue
            # radial gradient
            t = dist / R
            r = int(bg1[0] * t + bg2[0] * (1 - t))
            g = int(bg1[1] * t + bg2[1] * (1 - t))
            b = int(bg1[2] * t + bg2[2] * (1 - t))
            # soft edge anti-alias
            if dist > R - 1.5:
                alpha = int(255 * (R - dist) / 1.5)
            else:
                alpha = 255
            img[y][x] = (r, g, b, alpha)

    # ── Sound wave bars (5 bars, tallest in center) ───────────
    bar_color = (255, 255, 255)
    accent = (100, 180, 255)

    n_bars = 5
    heights_frac = [0.30, 0.55, 0.75, 0.55, 0.30]
    bar_w_frac = 0.07
    gap_frac = 0.035
    total_w = n_bars * bar_w_frac + (n_bars - 1) * gap_frac
    start_x_frac = 0.5 - total_w / 2

    bar_w = max(2, int(bar_w_frac * s))
    gap = max(1, int(gap_frac * s))
    center_y = int(s * 0.48)

    for i, h_frac in enumerate(heights_frac):
        bar_h = max(4, int(h_frac * s * 0.7))
        bx = int((start_x_frac + i * (bar_w_frac + gap_frac)) * s)
        by_top = center_y - bar_h // 2
        by_bot = center_y + bar_h // 2
        radius = bar_w // 2

        # pick color: center bar is accent, others white
        color = accent if i == 2 else bar_color

        for y in range(by_top, by_bot + 1):
            for x in range(bx, bx + bar_w):
                # anti-alias rounded caps
                dy_top = y - (by_top + radius)
                dy_bot = (by_bot - radius) - y
                dx_l = x - (bx + radius)
                dx_r = (bx + bar_w - radius) - x

                in_top_cap = dy_top < 0 and abs(x - (bx + radius)) > 0
                in_bot_cap = dy_bot < 0 and abs(x - (bx + radius)) > 0

                if dy_top < 0:
                    cdx = x - (bx + radius)
                    cdy = y - (by_top + radius)
                    d = math.sqrt(cdx ** 2 + cdy ** 2)
                    if d > radius + 0.5:
                        continue
                    alpha_fac = max(0, min(1, radius + 0.5 - d))
                elif dy_bot < 0:
                    cdx = x - (bx + radius)
                    cdy = y - (by_bot - radius)
                    d = math.sqrt(cdx ** 2 + cdy ** 2)
                    if d > radius + 0.5:
                        continue
                    alpha_fac = max(0, min(1, radius + 0.5 - d))
                else:
                    alpha_fac = 1.0

                r, g, b = color
                cr, cg, cb, ca = img[y][x]
                a = int(alpha_fac * 255)
                # blend over background
                out_r = (r * a + cr * (255 - a)) // 255
                out_g = (g * a + cg * (255 - a)) // 255
                out_b = (b * a + cb * (255 - a)) // 255
                img[y][x] = (out_r, out_g, out_b, ca)

    # ── Subtle arc lines on left/right (sound radiation) ──────
    arc_color = (100, 180, 255)
    for side in (-1, 1):
        for arc_idx, (arc_r_frac, arc_alpha) in enumerate([(0.38, 0.5), (0.46, 0.3)]):
            arc_r = arc_r_frac * s
            arc_thick = max(1, int(s * 0.025))
            for y in range(s):
                for x in range(s):
                    dx, dy = x - cx, y - cy
                    dist = math.sqrt(dx * dx + dy * dy)
                    if abs(dist - arc_r) <= arc_thick / 2:
                        # only left or right half
                        if side * dx < 0:
                            continue
                        # only middle vertical band
                        if abs(dy / s) > 0.35:
                            continue
                        fade = 1.0 - abs(dist - arc_r) / (arc_thick / 2)
                        a = int(fade * arc_alpha * 255)
                        r, g, b = arc_color
                        cr, cg, cb, ca = img[y][x]
                        out_r = (r * a + cr * (255 - a)) // 255
                        out_g = (g * a + cg * (255 - a)) // 255
                        out_b = (b * a + cb * (255 - a)) // 255
                        img[y][x] = (out_r, out_g, out_b, ca)

    # ── Encode PNG ─────────────────────────────────────────────
    def png_chunk(name: bytes, data: bytes) -> bytes:
        c = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", c)

    raw_rows = []
    for row in img:
        scanline = b"\x00"
        for r, g, b, a in row:
            scanline += bytes([r, g, b, a])
        raw_rows.append(scanline)

    compressed = zlib.compress(b"".join(raw_rows), 9)
    ihdr = struct.pack(">II", size, size) + bytes([8, 6, 0, 0, 0])

    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", compressed)
        + png_chunk(b"IEND", b"")
    )


def write_icns(path: str):
    type_map = {
        16:   b"icp4",
        32:   b"icp5",
        64:   b"icp6",
        128:  b"ic07",
        256:  b"ic08",
        512:  b"ic09",
        1024: b"ic10",
    }
    chunks = []
    for sz, tag in type_map.items():
        print(f"  rendering {sz}x{sz}...")
        png_data = make_png(sz)
        chunk_len = 8 + len(png_data)
        chunks.append(tag + struct.pack(">I", chunk_len) + png_data)

    body = b"".join(chunks)
    total = 8 + len(body)
    with open(path, "wb") as f:
        f.write(b"icns" + struct.pack(">I", total) + body)
    print(f"Written {path} ({total} bytes)")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AppIcon.icns")
    write_icns(out)
