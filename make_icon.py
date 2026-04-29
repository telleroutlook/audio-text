"""生成 AppIcon.icns 用于 macOS .app bundle"""

import struct
import zlib
import math
import os

def make_png(size: int) -> bytes:
    """Generate a microphone icon PNG at given size."""
    img = [[(0, 0, 0, 0)] * size for _ in range(size)]

    def fill_ellipse(cx, cy, rx, ry, color):
        for y in range(size):
            for x in range(size):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    img[y][x] = color

    def fill_rect(x1, y1, x2, y2, color):
        for y in range(max(0, y1), min(size, y2)):
            for x in range(max(0, x1), min(size, x2)):
                img[y][x] = color

    def fill_arc_outline(cx, cy, r, thickness, y_start_frac, y_end_frac, color):
        for y in range(size):
            for x in range(size):
                dx, dy = x - cx, y - cy
                dist = math.sqrt(dx * dx + dy * dy)
                if abs(dist - r) <= thickness / 2:
                    fy = y / size
                    if y_start_frac <= fy <= y_end_frac:
                        img[y][x] = color

    s = size
    # Background: rounded rect gradient-ish solid
    bg = (52, 120, 246, 255)      # vivid blue
    mic_body = (255, 255, 255, 255)
    mic_dark = (220, 235, 255, 255)

    # Background circle
    fill_ellipse(s // 2, s // 2, s // 2, s // 2, bg)

    # Mic body: rounded rectangle
    mw = int(s * 0.22)   # half-width
    mh = int(s * 0.30)   # half-height
    cx, cy_mid = s // 2, int(s * 0.42)
    # main rect
    fill_rect(cx - mw, cy_mid - mh, cx + mw, cy_mid + mh, mic_body)
    # top cap (ellipse)
    fill_ellipse(cx, cy_mid - mh, mw, mw, mic_body)
    # bottom cap (ellipse)
    fill_ellipse(cx, cy_mid + mh, mw, mw, mic_body)

    # Mic arc (stand)
    arc_r = int(s * 0.28)
    arc_cx, arc_cy = s // 2, int(s * 0.48)
    arc_thick = max(2, int(s * 0.045))
    # draw arc bottom half
    for y in range(size):
        for x in range(size):
            dx, dy = x - arc_cx, y - arc_cy
            dist = math.sqrt(dx * dx + dy * dy)
            if abs(dist - arc_r) <= arc_thick / 2 and dy >= 0:
                img[y][x] = mic_body

    # Stand post (vertical line)
    post_w = max(2, int(s * 0.045))
    post_top = arc_cy + arc_r
    post_bot = int(s * 0.83)
    fill_rect(cx - post_w // 2, post_top, cx + post_w // 2, post_bot, mic_body)

    # Base (horizontal bar)
    base_h = max(2, int(s * 0.045))
    base_w = int(s * 0.28)
    fill_rect(cx - base_w, post_bot - base_h // 2, cx + base_w, post_bot + base_h // 2 + 1, mic_body)

    # Encode as PNG
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

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2 | 4, 0, 0, 0)  # RGBA
    # bit depth=8, color type=6 (RGBA)
    ihdr = struct.pack(">II", size, size) + bytes([8, 6, 0, 0, 0])

    png = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", compressed)
        + png_chunk(b"IEND", b"")
    )
    return png


def write_icns(path: str):
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    # ICNS type codes for each size (1x, no retina distinction here)
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
    for sz in sizes:
        png_data = make_png(sz)
        tag = type_map[sz]
        chunk_len = 8 + len(png_data)
        chunks.append(tag + struct.pack(">I", chunk_len) + png_data)

    body = b"".join(chunks)
    total = 8 + len(body)
    with open(path, "wb") as f:
        f.write(b"icns" + struct.pack(">I", total) + body)
    print(f"Written {path} ({total} bytes)")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "AppIcon.icns")
    write_icns(out)
