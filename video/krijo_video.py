#!/usr/bin/env python3
"""
"Lamtumira e fundit" – film i shkurtër kinematografik vertikal (1080x1920)
për Instagram Reels.

Një çift (siluetë) ndahet nën dritën e një llambe rruge në shi.
Gjithçka gjenerohet me kod: grafika (Pillow + numpy), muzika (numpy) dhe
montazhi final (ffmpeg).

Elemente kinematografike: kuadro të ndryshme (plan i gjerë, plan i afërt,
detaj i duarve), kamerë që lëviz dhe dridhet lehtë, shirita kinemaje,
fokus i cekët (sfondi i turbullt), dritë kontre mbi silueta, reflektime në
rrugën e lagur, mjegull, shi në dy plane, "bloom", ngjyrim filmi dhe grimcë.

Përdorimi:
    python3 video/krijo_video.py            # krijon video/lamtumira_e_fundit.mp4
"""
import math
import os
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
DURATION = 34.0
GROUND = 1400
LAMP = (540, 764)
BAR = 170  # cinematic letterbox bars
SR = 44100

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "lamtumira_e_fundit.mp4")
WAV = os.path.join(HERE, "_muzika.wav")

FONT_SERIF_B = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_SERIF_I = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
FONT_SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

rng = np.random.default_rng(7)


# ---------------------------------------------------------------- helpers
def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ramp(t, a, b):
    return smooth((t - a) / (b - a))


def fade_window(t, start, end, f=0.45):
    return min(ramp(t, start, start + f), 1 - ramp(t, end - f, end))


# ---------------------------------------------------------------- camera
# (start, end, (cx, cy, zoom) at start, (cx, cy, zoom) at end)
SHOTS = [
    (0.0, 8.0, (540, 1150, 1.00), (540, 1120, 1.18)),    # establishing, slow push-in
    (8.0, 11.6, (540, 1060, 2.90), (540, 1040, 3.10)),   # close-up on the two faces
    (11.6, 14.0, (540, 1170, 4.20), (540, 1180, 4.60)),  # closer: hands letting go
    (14.0, 23.0, (540, 1150, 1.35), (540, 1110, 1.00)),  # wide, pulling out as they part
    (23.0, 25.6, (840, 1060, 2.40), (840, 1050, 2.60)),  # close on her, she looks back
    (25.6, 34.0, (540, 1150, 1.00), (540, 1160, 1.05)),  # wide: he is gone
]


def camera(t):
    for t0, t1, a, b in SHOTS:
        if t0 <= t < t1:
            k = smooth((t - t0) / (t1 - t0)) * 0.6 + (t - t0) / (t1 - t0) * 0.4
            cx, cy, z = (a[i] + (b[i] - a[i]) * k for i in range(3))
            break
    else:
        cx, cy, z = SHOTS[-1][3]
    # handheld breathing
    sx = 3.0 * (math.sin(t * 1.3) + 0.5 * math.sin(t * 2.9 + 1.0))
    sy = 2.5 * (math.sin(t * 1.1 + 2.0) + 0.5 * math.sin(t * 3.7))
    cx += sx / z
    cy += sy / z
    hw, hh = W / (2 * z), H / (2 * z)
    cx = min(max(cx, hw), W - hw)
    cy = min(max(cy, hh), H - hh)
    return cx, cy, z


def is_cut(t):
    return any(abs(t - s[0]) < 1e-6 for s in SHOTS[1:])


# ---------------------------------------------------------------- background
def build_background():
    y = np.linspace(0, 1, H)[:, None]
    top = np.array([6, 9, 26], float)
    mid = np.array([40, 30, 70], float)
    sky = np.where(y < 0.6, top + (mid - top) * (y / 0.6), mid)
    img = np.broadcast_to(sky[:, None, :], (H, W, 3)).copy()

    for _ in range(140):  # stars
        sx, sy = rng.integers(0, W), rng.integers(0, 700)
        img[sy:sy + 2, sx:sx + 2] = 120 + rng.integers(0, 100)

    pil = Image.fromarray(img.clip(0, 255).astype(np.uint8))

    halo = Image.new("L", (W, H), 0)
    ImageDraw.Draw(halo).ellipse((760, 210, 980, 430), fill=90)
    halo = halo.filter(ImageFilter.GaussianBlur(60))
    pil = Image.composite(Image.new("RGB", (W, H), (190, 190, 230)), pil, halo)
    d = ImageDraw.Draw(pil)
    d.ellipse((815, 265, 925, 375), fill=(232, 230, 245))

    windows = Image.new("RGB", (W, H), (0, 0, 0))
    wd = ImageDraw.Draw(windows)
    for layer, (col, base_h, win_p) in enumerate(
        [((24, 20, 46), 520, 0.10), ((14, 12, 28), 380, 0.16)]
    ):
        x = -20
        while x < W:
            bw = int(rng.integers(90, 190))
            bh = int(base_h + rng.integers(-120, 260))
            top_y = GROUND - bh - (120 if layer == 0 else 0)
            d.rectangle((x, top_y, x + bw, GROUND), fill=col)
            for wy in range(top_y + 24, GROUND - 40, 46):
                for wx in range(x + 16, x + bw - 24, 34):
                    if rng.random() < win_p:
                        warm = (255, 200, 110) if rng.random() < 0.8 else (160, 200, 255)
                        dim = 0.55 if layer == 0 else 0.85
                        c = tuple(int(v * dim) for v in warm)
                        d.rectangle((wx, wy, wx + 14, wy + 20), fill=c)
                        wd.rectangle((wx, wy, wx + 14, wy + 20), fill=c)
            x += bw + int(rng.integers(0, 20))

    # shallow depth of field: the city behind the couple is out of focus,
    # its windows bloom into soft bokeh
    pil = pil.filter(ImageFilter.GaussianBlur(3))
    bokeh = np.asarray(windows.filter(ImageFilter.GaussianBlur(11)), np.float32) * 2.2
    arr = np.asarray(pil).astype(np.float32) + bokeh

    gy = np.linspace(0, 1, H - GROUND)[:, None, None]
    arr[GROUND:] = np.array([18, 16, 30]) * (1 - gy) + np.array([6, 6, 12]) * gy
    # blurred, wet reflection of the city lights on the street
    refl = np.asarray(windows.filter(ImageFilter.GaussianBlur(16)), np.float32)[::-1]
    n = H - GROUND
    arr[GROUND:] += refl[H - GROUND:H - GROUND + n] * 0.9 * (1 - gy)
    arr[GROUND:GROUND + 6] = [55, 50, 80]
    pil = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(pil)

    # lamp post (in focus, same plane as the couple)
    d.rectangle((533, 760, 547, GROUND), fill=(10, 10, 16))
    d.rectangle((520, GROUND - 30, 560, GROUND), fill=(10, 10, 16))
    d.polygon([(500, 760), (580, 760), (565, 730), (515, 730)], fill=(10, 10, 16))
    d.ellipse((518, 752, 562, 776), fill=(255, 235, 180))
    return np.asarray(pil).astype(np.float32)


def build_light():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cone = np.zeros((H, W), np.float32)
    inside = (yy > 765) & (yy < GROUND + 10)
    spread = 30 + (yy - 765) * 0.42
    cone[inside] = np.clip(1 - np.abs(xx[inside] - 540) / spread[inside], 0, 1) ** 1.6 * 0.55
    bulb = np.exp(-(((xx - 540) ** 2 + (yy - 764) ** 2) / (2 * 55 ** 2))) * 1.2
    pool = np.exp(-(((xx - 540) / 260) ** 2 + ((yy - GROUND - 30) / 45) ** 2)) * 0.6
    streak = np.exp(-((xx - 540) / 40) ** 2) * np.exp(-((yy - GROUND) / 330)) * (yy > GROUND) * 0.5
    total = cone + bulb + pool + streak
    col = np.array([255, 205, 130], np.float32) / 255.0
    return total[..., None] * col[None, None, :] * 110


def build_vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.72)) ** 2 + ((yy - H * 0.52) / (H * 0.58)) ** 2)
    return np.clip(1.15 - r ** 2 * 0.85, 0.18, 1.0)[..., None]


def build_mist():
    small = rng.random((24, 90)).astype(np.float32)
    big = Image.fromarray((small * 255).astype(np.uint8)).resize((W * 3, 700), Image.BICUBIC)
    big = big.filter(ImageFilter.GaussianBlur(30))
    a = np.asarray(big, np.float32) / 255.0
    a = (a - a.min()) / (a.max() - a.min())
    return a


# ---------------------------------------------------------------- characters
SS = 2  # supersampling for smooth silhouettes


def draw_person(d, T, z, x, facing, phase, female, arm_target=None, bow=0.0, look_back=0.0):
    """Draw a silhouette. World coordinates go through camera transform T."""
    Ht = 430 if not female else 400
    gy = GROUND
    r = Ht * 0.075
    head = (x + facing * bow * 14 - look_back * facing * 6, gy - Ht + r + bow * 6)
    sh_y = gy - Ht + 2 * r + 10
    hip_y = gy - Ht * 0.48
    wsh = 34 if female else 48
    whip = 30 if female else 34
    k = SS * z

    def limb(a, b, w):
        d.line([T(*a), T(*b)], fill=255, width=max(1, int(w * k)))
        bx, by = T(*b)
        rr = w * k / 2
        d.ellipse([bx - rr, by - rr, bx + rr, by + rr], fill=255)

    def poly(pts):
        d.polygon([T(*p) for p in pts], fill=255)

    def ell(x0, y0, x1, y1):
        a, b = T(x0, y0), T(x1, y1)
        d.ellipse([a[0], a[1], b[0], b[1]], fill=255)

    L = gy - hip_y
    swing = math.sin(phase) * 0.38
    for side, sgn in ((-1, 1), (1, -1)):
        hx = x + side * (9 if female else 12)
        a = sgn * swing
        foot = (hx + math.sin(a) * L, hip_y + math.cos(a) * L)
        knee = (hx + math.sin(a) * L * 0.5 + facing * abs(swing) * 8, hip_y + math.cos(a) * L * 0.5)
        limb((hx, hip_y), knee, 22 if female else 28)
        limb(knee, foot, 18 if female else 24)
        limb(foot, (foot[0] + facing * 18, foot[1]), 12)

    if female:
        waist = sh_y + Ht * 0.20
        poly([(x - wsh, sh_y), (x + wsh, sh_y), (x + 22, waist), (x - 22, waist)])
        poly([(x - 22, waist), (x + 22, waist), (x + 62, hip_y + 70), (x - 62, hip_y + 70)])
    else:
        poly([(x - wsh, sh_y + 10), (x - wsh * 0.45, sh_y - 4), (x + wsh * 0.45, sh_y - 4), (x + wsh, sh_y + 10),
              (x + whip, hip_y + 10), (x - whip, hip_y + 10)])
        # coat collar
        poly([(x - 20, sh_y - 4), (x + 20, sh_y - 4), (x + 12, sh_y + 14), (x - 12, sh_y + 14)])
    ell(x - wsh - 8, sh_y + 2, x - wsh + 16, sh_y + 26)
    ell(x + wsh - 16, sh_y + 2, x + wsh + 8, sh_y + 26)

    limb((x, sh_y), (x + facing * bow * 6, head[1] + r * 0.6), 18)
    ell(head[0] - r, head[1] - r, head[0] + r, head[1] + r)
    # nose profile so faces read in close-ups
    poly([(head[0] + facing * r * 0.85, head[1] - r * 0.15), (head[0] + facing * (r + 7), head[1] + r * 0.18),
          (head[0] + facing * r * 0.8, head[1] + r * 0.3)])
    if female:
        back = -facing
        ell(head[0] - r - 5, head[1] - r - 6, head[0] + r + 5, head[1] + r * 0.6)
        poly([(head[0] + back * (r + 4), head[1] - 4), (head[0] - back * r * 0.2, head[1]),
              (head[0] + back * 10, sh_y + 80), (head[0] + back * (r + 18), sh_y + 70)])

    arm_len = Ht * 0.40
    for side in (-1, 1):
        shx = x + side * (wsh - 4)
        if arm_target is not None and side == arm_target[2]:
            tx, ty, _, amt = arm_target
            rest = (shx + side * 6, sh_y + arm_len)
            tx = rest[0] + (tx - rest[0]) * amt
            ty = rest[1] + (ty - rest[1]) * amt
            dx, dy = tx - shx, ty - sh_y
            dist = math.hypot(dx, dy)
            kk = min(1.0, arm_len / max(dist, 1))
            hand = (shx + dx * kk, sh_y + dy * kk)
            elbow = ((shx + hand[0]) / 2, (sh_y + hand[1]) / 2 + 10)
        else:
            a = -side * math.sin(phase) * 0.3 * (1 if facing > 0 else -1) + side * 0.08
            elbow = (shx + math.sin(a) * arm_len * 0.5, sh_y + math.cos(a) * arm_len * 0.5)
            hand = (shx + math.sin(a * 1.2) * arm_len + facing * abs(math.sin(phase)) * 6,
                    sh_y + math.cos(a * 1.2) * arm_len)
        limb((shx, sh_y + 6), elbow, 15 if female else 18)
        limb(elbow, hand, 13 if female else 16)
        ell(hand[0] - 9, hand[1] - 7, hand[0] + 9, hand[1] + 11)


# ---------------------------------------------------------------- heart
def heart_points(cx, cy, size, n=120):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * size / 16, cy + y * size / 16))
    return pts


def build_heart_halves(size=80):
    S = 2 * size + 40
    full = Image.new("L", (S * SS, S * SS), 0)
    ImageDraw.Draw(full).polygon([(px * SS, py * SS) for px, py in heart_points(S / 2, S / 2 + 6, size)], fill=255)
    crack = [(S / 2 + 2, 0), (S / 2 - 12, S * 0.32), (S / 2 + 10, S * 0.48),
             (S / 2 - 8, S * 0.66), (S / 2 + 4, S)]
    left_mask = Image.new("L", full.size, 0)
    ImageDraw.Draw(left_mask).polygon([(0, 0)] + [(a * SS, b * SS) for a, b in crack] + [(0, S * SS)], fill=255)
    fa, la = np.asarray(full, np.float32), np.asarray(left_mask, np.float32) / 255
    return [Image.fromarray(arr.astype(np.uint8)) for arr in (fa, fa * la, fa * (1 - la))]  # at SS scale


def paste_shape(frame, img, cx, cy, color, alpha, glow=0.0):
    """Alpha-blend an L-mode shape centred at (cx, cy) with clipping."""
    a = np.asarray(img, np.float32)[..., None] / 255.0 * alpha
    g = None
    if glow:
        g = np.asarray(img.filter(ImageFilter.GaussianBlur(max(4, img.width // 14))), np.float32)[..., None] / 255.0
    h, w = a.shape[:2]
    x0, y0 = int(cx - w / 2), int(cy - h / 2)
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if fx0 >= fx1 or fy0 >= fy1:
        return
    sa = a[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
    sub = frame[fy0:fy1, fx0:fx1]
    sub[:] = sub * (1 - sa) + color * sa
    if g is not None:
        sub += color * glow * g[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0] * alpha


# ---------------------------------------------------------------- text
_text_cache = {}


def text_layer(text, font_path, size, color=(255, 255, 255), y=1560, spacing=0):
    key = (text, font_path, size, color, y, spacing)
    if key in _text_cache:
        return _text_cache[key]
    font = ImageFont.truetype(font_path, size)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    lines = text.split("\n")
    lh = int(size * 1.3)
    total = lh * len(lines)
    for i, line in enumerate(lines):
        chars = list(line)
        widths = [d.textlength(c, font=font) + spacing for c in chars]
        lw = sum(widths) - (spacing if chars else 0)
        tx, ty = W / 2 - lw / 2, y - total / 2 + i * lh
        for c, cw in zip(chars, widths):
            d.text((tx + 2, ty + 3), c, font=font, fill=(0, 0, 0, 200))
            d.text((tx, ty), c, font=font, fill=color + (255,))
            tx += cw
    # soft shadow so subtitles read over rain
    shadow = layer.split()[3].filter(ImageFilter.GaussianBlur(10))
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    base.putalpha(shadow.point(lambda v: int(v * 0.7)))
    layer = Image.alpha_composite(base, layer)
    arr = np.asarray(layer)
    rows = np.nonzero(arr[..., 3].any(1))[0]
    y0, y1 = int(rows[0]), int(rows[-1]) + 1
    arr = arr[y0:y1].astype(np.float32)
    res = (arr[..., :3], arr[..., 3:] / 255.0, y0, y1)
    _text_cache[key] = res
    return res


def blend_text(frame, layer, alpha):
    if alpha <= 0.001:
        return frame
    rgb, a, y0, y1 = layer
    a = a * alpha
    frame[y0:y1] = frame[y0:y1] * (1 - a) + rgb * a
    return frame


SUB_Y = 1590
CAPTIONS = [
    # start, end, text, font, size, y, letter-spacing
    (0.4, 3.6, "LAMTUMIRA\nE FUNDIT", FONT_SERIF_B, 84, 880, 14),
    (1.3, 3.6, "shikoje deri në fund…", FONT_SERIF_I, 46, 1080, 2),
    (4.4, 7.8, "— A më do akoma?", FONT_SERIF_I, 56, SUB_Y, 1),
    (8.3, 10.8, "— …Nuk e di më.", FONT_SERIF_I, 56, SUB_Y, 1),
    (11.2, 14.2, "Disa heshtje flasin\nmë shumë se fjalët.", FONT_SERIF_I, 54, SUB_Y, 1),
    (14.6, 18.6, "Ai zgjodhi krenarinë.", FONT_SERIF_I, 56, SUB_Y, 1),
    (18.8, 22.8, "Ajo zgjodhi veten.", FONT_SERIF_I, 56, SUB_Y, 1),
    (23.4, 27.6, "Ajo u kthye të shikonte…\nai jo.", FONT_SERIF_I, 56, SUB_Y, 1),
    (28.6, 34.0, "Disa njerëz janë kapituj,\njo e gjithë historia.", FONT_SERIF_B, 54, 860, 2),
    (30.6, 34.0, "Shëno dikë që duhet ta shohë këtë.", FONT_SANS_B, 38, 1480, 1),
]


# ---------------------------------------------------------------- rain
N_FAR, N_NEAR = 420, 55
far = np.stack([rng.uniform(-200, W + 200, N_FAR), rng.uniform(0, H, N_FAR),
                rng.uniform(1300, 2100, N_FAR), rng.uniform(30, 70, N_FAR)], 1)
near = np.stack([rng.uniform(-200, W + 200, N_NEAR), rng.uniform(0, H, N_NEAR),
                 rng.uniform(2600, 3400, N_NEAR), rng.uniform(110, 190, N_NEAR)], 1)


def draw_rain(pil, t, intensity):
    d = ImageDraw.Draw(pil)
    for drops, width, base in ((far, 2, 115), (near, 4, 150)):
        n = int(len(drops) * intensity)
        for x0, y0, v, ln in drops[:n]:
            y = (y0 + v * t) % (H + 300) - 200
            x = ((x0 - 0.12 * (y - y0)) % (W + 200)) - 100
            c = base + int(ln * 0.3)
            d.line((x, y, x - ln * 0.12, y + ln), fill=(c, c + 8, c + 30), width=width)


def draw_splashes(pil, fi, T, z):
    d = ImageDraw.Draw(pil)
    r = np.random.default_rng(1000 + fi)
    for _ in range(26):
        wx, wy = r.uniform(0, W), GROUND + r.uniform(8, 380)
        sx, sy = T(wx, wy)
        sx, sy = sx / SS, sy / SS
        if 0 <= sx < W and 0 <= sy < H:
            rw = (3 + r.uniform(0, 7)) * z * (0.6 + (wy - GROUND) / 380)
            d.ellipse((sx - rw, sy - rw * 0.25, sx + rw, sy + rw * 0.25), outline=(120, 125, 150), width=1)


# ---------------------------------------------------------------- story state
def state(t):
    he = dict(x=486.0, facing=1, phase=0.0, bow=0.0, look=0.0)
    she = dict(x=594.0, facing=-1, phase=0.0, bow=0.0, look=0.0)
    hold = 1 - ramp(t, 12.0, 12.9)         # fingers slip apart in the close-up
    she["bow"] = ramp(t, 8.6, 9.6)          # she lowers her head: "nuk e di më"
    he["bow"] = ramp(t, 11.0, 12.0)
    if t >= 13.4:
        he["facing"], she["facing"] = -1, 1
    vh, vs = 40.0, 36.0
    if t > 14.0:
        dh = vh * (t - 14.0)
        he["x"] -= dh
        he["phase"] = dh / 24.0
    ts = min(t, 22.0)
    if ts > 14.0:
        ds = vs * (ts - 14.0)
        she["x"] += ds
        she["phase"] = ds / 22.0
        if t >= 22.0:
            she["phase"] = round(she["phase"] / math.pi) * math.pi
    if t > 23.7:                            # she turns back to look at him
        she["facing"] = -1
        she["look"] = 1.0
    return he, she, hold


# ---------------------------------------------------------------- grading
def grade(frame):
    lum = frame.mean(-1, keepdims=True) / 255.0
    # teal shadows, warm highlights
    frame = frame * (1 + (1 - lum) * np.array([-0.10, 0.02, 0.12], np.float32)) \
                  * (1 + lum * np.array([0.12, 0.03, -0.10], np.float32))
    # gentle S-curve
    x = np.clip(frame / 255.0, 0, 1)
    s = x * x * (3 - 2 * x)
    return (x * 0.65 + s * 0.35) * 255.0


def bloom(frame):
    small = Image.fromarray(frame.clip(0, 255).astype(np.uint8)).resize((W // 6, H // 6), Image.BILINEAR)
    b = np.asarray(small, np.float32)
    b = np.clip(b - 140, 0, None) * 1.4
    b = Image.fromarray(b.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))
    b = np.asarray(b.resize((W, H), Image.BILINEAR), np.float32)
    return frame + b * 0.55


# ---------------------------------------------------------------- render
def main():
    bg = build_background()
    light = build_light()
    bg_bright = Image.fromarray((bg + light).clip(0, 255).astype(np.uint8))
    bg_dim = Image.fromarray((bg + light * 0.45).clip(0, 255).astype(np.uint8))
    vig = build_vignette()
    mist = build_mist()
    heart_full, heart_l, heart_r = build_heart_halves()
    shadow_col = np.array([7, 6, 14], np.float32)
    rim_col = np.array([255, 200, 135], np.float32)
    heart_col = np.array([225, 25, 55], np.float32)
    xs = np.arange(W, dtype=np.float32)

    preview = os.environ.get("PREVIEW")  # e.g. PREVIEW=6,12.5,24 -> PNG stills only
    if preview:
        frames = [int(float(v) * FPS) for v in preview.split(",")]
    else:
        frames = range(int(DURATION * FPS))
        write_music()

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", WAV,
           "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    ff = None if preview else subprocess.Popen(cmd, stdin=subprocess.PIPE)

    n_frames = int(DURATION * FPS)
    for fi in frames:
        t = fi / FPS
        cx, cy, z = camera(t)

        def T(px, py):
            return (((px - cx) * z + W / 2) * SS, ((py - cy) * z + H / 2) * SS)

        flick = 1.0
        if 10.8 < t < 13.0:
            flick = 1.0 if math.sin(t * 47) > -0.2 and math.sin(t * 13) > -0.7 else 0.0

        # background through the camera (zoomed areas get softer = depth of field)
        hw, hh = W / (2 * z), H / (2 * z)
        box = (cx - hw, cy - hh, cx + hw, cy + hh)
        src = bg_bright if flick else bg_dim
        frame = np.asarray(src.resize((W, H), Image.BICUBIC, box=box), np.float32).copy()

        # mist drifting along the street
        gs = (GROUND - cy) * z + H / 2
        m_y0 = int(gs - 420 * z)
        mh = int(700 * z)
        if m_y0 < H and m_y0 + mh > 0:
            off = int((t * 18) % (W * 2))
            band = mist[:, off:off + W]
            band = np.asarray(Image.fromarray((band * 255).astype(np.uint8)).resize((W, max(1, mh)), Image.BILINEAR),
                              np.float32)[..., None] / 255.0
            fy0, fy1 = max(0, m_y0), min(H, m_y0 + mh)
            frame[fy0:fy1] += band[fy0 - m_y0:fy1 - m_y0] * np.array([70, 70, 100], np.float32) * 0.55

        # characters
        he, she, hold = state(t)
        mask = Image.new("L", (W * SS, H * SS), 0)
        md = ImageDraw.Draw(mask)
        sh_y = GROUND - 430 + 2 * 430 * 0.075 + 10
        meet = ((he["x"] + she["x"]) / 2, sh_y + 150)
        draw_person(md, T, z, he["x"], he["facing"], he["phase"], False,
                    arm_target=(meet[0], meet[1], 1, hold) if hold > 0.01 and he["facing"] == 1 else None,
                    bow=he["bow"])
        draw_person(md, T, z, she["x"], she["facing"], she["phase"], True,
                    arm_target=(meet[0] + 4, meet[1] + 6, -1, hold) if hold > 0.01 and she["facing"] == -1 else None,
                    bow=she["bow"], look_back=she["look"])
        m = np.asarray(mask.resize((W, H), Image.BILINEAR), np.float32) / 255.0

        # rim light from the street lamp on the silhouettes
        k = max(2, int(1.6 * z))
        top = np.clip(m - np.roll(m, k, axis=0), 0, 1)
        left_edges = np.clip(m - np.roll(m, k, axis=1), 0, 1)
        right_edges = np.clip(m - np.roll(m, -k, axis=1), 0, 1)
        lamp_sx = (LAMP[0] - cx) * z + W / 2
        side = np.where(xs[None, :] < lamp_sx, right_edges, left_edges)
        wx = (xs - W / 2) / z + cx
        inten = np.exp(-((wx - LAMP[0]) / 300.0) ** 2)[None, :] * (0.35 + 0.65 * flick)
        rim = np.clip(top * 0.9 + side * 0.8, 0, 1) * inten
        rim = np.asarray(Image.fromarray((rim * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)),
                         np.float32) / 255.0

        m3 = m[..., None]
        frame = frame * (1 - m3) + shadow_col * m3
        frame += rim[..., None] * rim_col * 0.9

        # reflection of the couple in the wet street
        g = int(gs)
        if 0 < g < H - 8:
            rows = np.arange(g + 4, H)
            srcr = 2 * g - rows
            ok = srcr >= 0
            rows, srcr = rows[ok], srcr[ok]
            fall = np.clip(1 - (rows - g) / (500 * z), 0, 1)[:, None, None] * 0.32
            refl = m[srcr][..., None] * fall
            frame[rows] = frame[rows] * (1 - refl) + shadow_col * refl

        # heart between them
        if 4.0 < t < 11.6:
            ha = ramp(t, 4.0, 5.2)
            hx, hy = (540 - cx) * z + W / 2, (930 - cy) * z + H / 2
            base = 0.5 * z  # heart images are at SS scale (2x)
            if t < 10.8:
                beat = 1 + 0.09 * max(0, math.sin(t * 2 * math.pi * 1.1)) ** 6
                sz = max(4, int(heart_full.width * base * beat))
                paste_shape(frame, heart_full.resize((sz, sz), Image.BILINEAR), hx, hy, heart_col, ha, glow=0.6)
            else:
                kk = ramp(t, 10.8, 11.6)
                fade = 1 - ramp(t, 11.15, 11.6)
                sz = max(4, int(heart_full.width * base))
                for img, sgn in ((heart_l, -1), (heart_r, 1)):
                    hi = img.resize((sz, sz), Image.BILINEAR).rotate(-sgn * 22 * kk, resample=Image.BILINEAR)
                    paste_shape(frame, hi, hx + sgn * 70 * z * kk, hy + 170 * z * kk * kk,
                                heart_col, ha * fade, glow=0.5)

        frame = bloom(frame)
        frame = grade(frame)
        frame *= vig

        pil = Image.fromarray(frame.clip(0, 255).astype(np.uint8))
        draw_rain(pil, t, 0.4 + 0.6 * ramp(t, 10.8, 15.0))
        draw_splashes(pil, fi, T, z)
        frame = np.asarray(pil).astype(np.float32)

        # fade in from black, hard cuts with a 2-frame dip, fade out to end card
        scene_a = ramp(t, 3.0, 4.6) * (1 - ramp(t, 27.4, 28.6))
        if any(0 <= t - s[0] < 2 / FPS for s in SHOTS[1:]):
            scene_a *= 0.35
        frame *= scene_a

        # broken heart on the end card
        if t > 28.4:
            a = ramp(t, 28.6, 29.6)
            for img, dx in ((heart_l, -16), (heart_r, 16)):
                hi = img.resize((img.width // 4, img.height // 4), Image.LANCZOS)
                paste_shape(frame, hi, 540 + dx, 1180, heart_col, a, glow=0.8)

        for start, end, text, font, size, y, sp in CAPTIONS:
            if start - 0.05 <= t <= end + 0.05:
                frame = blend_text(frame, text_layer(text, font, size, y=y, spacing=sp),
                                   fade_window(t, start, end))

        # letterbox bars slide in with the first shot
        bar = int(BAR * ramp(t, 2.6, 4.0)) if t < 28.0 else int(BAR * (1 - ramp(t, 28.0, 29.0)))
        if bar > 0:
            frame[:bar] = 0
            frame[H - bar:] = 0

        frame += rng.normal(0, 5, (H // 3, W // 3, 1)).repeat(3, 0).repeat(3, 1)

        if preview:
            Image.fromarray(frame.clip(0, 255).astype(np.uint8)).save(os.path.join(preview_dir(), f"kuadri_{t:05.1f}.png"))
            continue
        ff.stdin.write(frame.clip(0, 255).astype(np.uint8).tobytes())
        if fi % 60 == 0:
            print(f"  kuadri {fi}/{n_frames}", flush=True)

    if preview:
        return
    ff.stdin.close()
    ff.wait()
    os.remove(WAV)
    print("Gati:", OUT)


def preview_dir():
    d = os.environ.get("PREVIEW_DIR", HERE)
    os.makedirs(d, exist_ok=True)
    return d


# ---------------------------------------------------------------- music
def note_freq(name):
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[n] + 12 * (o - 4) - 9) / 12)


def piano(freq, dur, vel=1.0):
    t = np.arange(int(dur * SR)) / SR
    env = np.exp(-t * 2.2) * np.minimum(1, t / 0.006)
    sig = sum((1 / k ** 1.6) * np.sin(2 * np.pi * freq * k * t * (1 + 0.0004 * k)) for k in range(1, 7))
    return sig * env * vel


def strings(freqs, dur, vol):
    t = np.arange(int(dur * SR)) / SR
    vib = 1 + 0.003 * np.sin(2 * np.pi * 5.2 * t)
    sig = np.zeros_like(t)
    for f in freqs:
        for det in (0.997, 1.0, 1.004):
            ph = 2 * np.pi * f * det * np.cumsum(vib) / SR
            sig += np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.5
    return sig * env * vol


def write_music():
    total = int(DURATION * SR)
    music = np.zeros(total + SR * 4)
    fx = np.zeros_like(music)

    def add(buf, sig, at):
        i = int(at * SR)
        buf[i:i + len(sig)] += sig[: len(buf) - i]

    chords = [
        ("A2", ["A3", "C4", "E4", "A4"]),
        ("F2", ["F3", "A3", "C4", "F4"]),
        ("C3", ["C4", "E4", "G4", "C5"]),
        ("G2", ["G3", "B3", "D4", "G4"]),
    ]
    melody = ["E5", None, "C5", "D5", "C5", None, "A4", None,
              "G4", None, "E4", "G4", "A4", None, None, None,
              "E5", None, "G5", "E5", "D5", None, "C5", None,
              "B4", None, "G4", None, "A4", None, None, None]
    beat = 0.5
    t = 0.0
    bar = 0
    while t < DURATION - 1:
        bass, notes = chords[bar % 4]
        add(music, piano(note_freq(bass), 4.0, 0.55), t)
        for i in range(8):
            n = notes[[0, 1, 2, 3, 2, 1, 2, 3][i]]
            add(music, piano(note_freq(n), 2.0, 0.20), t + i * beat)
        if t >= 4.0:
            for i in range(8):
                m = melody[(bar * 8 + i) % len(melody)]
                if m:
                    add(music, piano(note_freq(m), 2.5, 0.30), t + i * beat)
        # strings swell bigger in the second half
        vol = 0.012 if t < 4 else (0.03 if t < 14 else 0.05)
        add(music, strings([note_freq(n) / 2 for n in notes[:3]], 4.4, vol), t - 0.2 if t > 0 else 0)
        t += 8 * beat
        bar += 1

    # riser into the heartbreak, then a deep cinematic hit
    n = int(1.5 * SR)
    tt = np.arange(n) / SR
    noise = np.convolve(rng.normal(0, 1, n), np.ones(12) / 12, mode="same")
    add(fx, noise * (tt / 1.5) ** 3 * 0.5, 9.3)
    tt = np.arange(int(3.5 * SR)) / SR
    boom = (np.sin(2 * np.pi * (52 - 18 * tt) * tt) * np.exp(-tt * 1.6) * 1.2
            + rng.normal(0, 1, len(tt)) * np.exp(-tt * 9) * 0.25)
    add(fx, boom, 10.8)
    # low drone under the final shots
    tt = np.arange(int(12 * SR)) / SR
    drone = np.sin(2 * np.pi * 55 * tt) * 0.5 + np.sin(2 * np.pi * 82.4 * tt) * 0.3
    add(fx, drone * np.sin(np.pi * tt / 12) ** 2 * 0.25, 18.0)

    # music drops out for a breath right after the hit
    tl_all = np.arange(len(music)) / SR
    duck = 1 - 0.75 * np.clip(1 - np.abs(tl_all - 11.6) / 0.9, 0, 1)
    out = music * duck + fx

    dry = out.copy()
    for delay, g in ((0.0297, 0.65), (0.0371, 0.6), (0.0411, 0.55), (0.0437, 0.5)):
        dsm = int(delay * SR)
        y = dry.copy()
        for i in range(dsm, len(y), dsm):
            y[i:i + dsm] += g * y[i - dsm:i][: len(y[i:i + dsm])]
        out += y * 0.2

    out = out[:total]
    noise = np.convolve(rng.normal(0, 1, total), np.ones(8) / 8, mode="same")
    tl = np.arange(total) / SR
    rain_amt = 0.05 + 0.07 * np.clip((tl - 10.8) / 4, 0, 1)
    out = out / (np.abs(out).max() + 1e-9) * 0.8 + noise * rain_amt
    out *= np.clip(tl / 1.0, 0, 1) * np.clip((DURATION - tl) / 2.5, 0, 1)
    out = out / (np.abs(out).max() + 1e-9) * 0.9
    pcm = (out * 32767).astype(np.int16)
    with wave.open(WAV, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(np.stack([pcm, pcm], 1).tobytes())


if __name__ == "__main__":
    main()
