#!/usr/bin/env python3
"""
"Lamtumira e fundit" – film i shkurtër vertikal (1080x1920) për Instagram Reels.

Një çift (siluetë) ndahet nën dritën e një llambe rruge në shi.
Gjithçka gjenerohet me kod: grafika (Pillow + numpy), muzika (numpy) dhe
montazhi final (ffmpeg).

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


# ---------------------------------------------------------------- background
def build_background():
    y = np.linspace(0, 1, H)[:, None]
    top = np.array([8, 10, 28], float)
    mid = np.array([38, 28, 68], float)
    sky = np.where(y < 0.6, top + (mid - top) * (y / 0.6), mid)
    img = np.repeat(sky, W, axis=1).reshape(H, W, 3).copy()

    # stars
    for _ in range(140):
        sx, sy = rng.integers(0, W), rng.integers(0, 700)
        img[sy:sy + 2, sx:sx + 2] = 120 + rng.integers(0, 100)

    pil = Image.fromarray(img.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(pil)

    # moon with halo
    halo = Image.new("L", (W, H), 0)
    ImageDraw.Draw(halo).ellipse((760, 210, 980, 430), fill=90)
    halo = halo.filter(ImageFilter.GaussianBlur(60))
    pil = Image.composite(Image.new("RGB", (W, H), (190, 190, 230)), pil, halo)
    d = ImageDraw.Draw(pil)
    d.ellipse((815, 265, 925, 375), fill=(232, 230, 245))

    # city skyline, two layers
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
                        d.rectangle((wx, wy, wx + 14, wy + 20),
                                    fill=tuple(int(c * dim) for c in warm))
            x += bw + int(rng.integers(0, 20))

    # wet street
    arr = np.asarray(pil).astype(float)
    gy = np.linspace(0, 1, H - GROUND)[:, None, None]
    street = np.array([18, 16, 30]) * (1 - gy) + np.array([6, 6, 12]) * gy
    arr[GROUND:] = street
    # sidewalk edge
    arr[GROUND:GROUND + 6] = [55, 50, 80]
    pil = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(pil)

    # lamp post
    d.rectangle((533, 760, 547, GROUND), fill=(10, 10, 16))
    d.rectangle((520, GROUND - 30, 560, GROUND), fill=(10, 10, 16))
    d.polygon([(500, 760), (580, 760), (565, 730), (515, 730)], fill=(10, 10, 16))
    d.ellipse((518, 752, 562, 776), fill=(255, 235, 180))
    return np.asarray(pil).astype(np.float32)


def build_light():
    """Additive light: lamp cone + ground pool + reflection streak."""
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
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.55) / (H * 0.62)) ** 2)
    return np.clip(1.15 - r ** 2 * 0.75, 0.25, 1.0)[..., None]


# ---------------------------------------------------------------- characters
SS = 2  # supersampling for smooth silhouettes
BAND_Y0, BAND_Y1 = 760, GROUND + 4  # vertical band where figures live


def draw_person(d, x, facing, phase, female, arm_target=None, bow=0.0, look_back=0.0):
    """Draw a silhouette into ImageDraw `d` (band coordinates, SS scale)."""
    s = SS
    Ht = 430 if not female else 400
    gy = (GROUND - BAND_Y0)
    r = Ht * 0.075
    head = (x + facing * bow * 14 - look_back * facing * 6, gy - Ht + r)
    sh_y = gy - Ht + 2 * r + 10
    hip_y = gy - Ht * 0.48
    wsh = 34 if female else 48
    whip = 30 if female else 34

    def P(px, py):
        return (px * s, py * s)

    def limb(a, b, w):
        d.line([P(*a), P(*b)], fill=255, width=int(w * s))
        d.ellipse([P(b[0] - w / 2, b[1] - w / 2), P(b[0] + w / 2, b[1] + w / 2)], fill=255)

    # legs
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

    # torso
    if female:
        waist = sh_y + Ht * 0.20
        d.polygon([P(x - wsh, sh_y), P(x + wsh, sh_y), P(x + 22, waist), P(x - 22, waist)], fill=255)
        d.polygon([P(x - 22, waist), P(x + 22, waist), P(x + 62, hip_y + 70), P(x - 62, hip_y + 70)], fill=255)
    else:
        d.polygon([P(x - wsh, sh_y), P(x + wsh, sh_y), P(x + whip, hip_y + 10), P(x - whip, hip_y + 10)], fill=255)
    d.ellipse([P(x - wsh - 8, sh_y - 8), P(x - wsh + 16, sh_y + 22)], fill=255)
    d.ellipse([P(x + wsh - 16, sh_y - 8), P(x + wsh + 8, sh_y + 22)], fill=255)

    # neck + head
    limb((x, sh_y), (x + facing * bow * 6, head[1] + r * 0.6), 18)
    d.ellipse([P(head[0] - r, head[1] - r), P(head[0] + r, head[1] + r)], fill=255)
    if female:  # long hair falling on the back side
        back = -facing if look_back < 0.5 else facing
        d.ellipse([P(head[0] - r - 5, head[1] - r - 6), P(head[0] + r + 5, head[1] + r * 0.6)], fill=255)
        d.polygon([P(head[0] + back * (r + 4), head[1] - 4), P(head[0] - back * r * 0.2, head[1]),
                   P(head[0] + back * 10, sh_y + 80), P(head[0] + back * (r + 18), sh_y + 70)], fill=255)

    # arms
    arm_len = Ht * 0.40
    for side in (-1, 1):
        shx = x + side * (wsh - 4)
        if arm_target is not None and side == arm_target[2]:
            tx, ty = arm_target[0], arm_target[1]
            dx, dy = tx - shx, ty - sh_y
            dist = math.hypot(dx, dy)
            k = min(1.0, arm_len / max(dist, 1))
            hand = (shx + dx * k, sh_y + dy * k)
            elbow = ((shx + hand[0]) / 2, (sh_y + hand[1]) / 2 + 10)
        else:
            a = -side * math.sin(phase) * 0.3 * (1 if facing > 0 else -1) + side * 0.08
            elbow = (shx + math.sin(a) * arm_len * 0.5, sh_y + math.cos(a) * arm_len * 0.5)
            hand = (shx + math.sin(a * 1.2) * arm_len + facing * abs(math.sin(phase)) * 6,
                    sh_y + math.cos(a * 1.2) * arm_len)
        limb((shx, sh_y + 6), elbow, 15 if female else 18)
        limb(elbow, hand, 13 if female else 16)


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
    out = []
    for arr in (fa, fa * la, fa * (1 - la)):
        im = Image.fromarray(arr.astype(np.uint8)).resize((S, S), Image.LANCZOS)
        out.append(im)
    return out  # full, left, right


# ---------------------------------------------------------------- text
_text_cache = {}


def text_layer(text, font_path, size, color=(255, 255, 255), y=1560, box=True):
    key = (text, font_path, size, color, y, box)
    if key in _text_cache:
        return _text_cache[key]
    font = ImageFont.truetype(font_path, size)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    lines = text.split("\n")
    lh = int(size * 1.3)
    total = lh * len(lines)
    widths = [d.textlength(l, font=font) for l in lines]
    if box:
        bw = max(widths) + 70
        y0 = y - total / 2 - 26
        d.rounded_rectangle((W / 2 - bw / 2, y0, W / 2 + bw / 2, y0 + total + 40), 26, fill=(0, 0, 0, 120))
    for i, (line, wdt) in enumerate(zip(lines, widths)):
        ty = y - total / 2 + i * lh
        tx = W / 2 - wdt / 2
        d.text((tx + 3, ty + 3), line, font=font, fill=(0, 0, 0, 160))
        d.text((tx, ty), line, font=font, fill=color + (255,))
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


CAPTIONS = [
    # start, end, text, font, size, y
    (0.4, 3.6, "LAMTUMIRA\nE FUNDIT", FONT_SERIF_B, 96, 860),
    (1.3, 3.6, "shikoje deri në fund…", FONT_SERIF_I, 52, 1080),
    (4.4, 7.6, "— A më do akoma?", FONT_SERIF_I, 62, 1600),
    (7.6, 10.6, "— …Nuk e di më.", FONT_SERIF_I, 62, 1600),
    (10.8, 14.2, "Disa heshtje flasin\nmë shumë se fjalët.", FONT_SERIF_I, 58, 1600),
    (14.4, 18.6, "Ai zgjodhi krenarinë.", FONT_SERIF_I, 60, 1600),
    (18.6, 22.8, "Ajo zgjodhi veten.", FONT_SERIF_I, 60, 1600),
    (23.2, 27.8, "Ajo u kthye të shikonte…\nai jo.", FONT_SERIF_I, 60, 1600),
    (28.6, 34.0, "Disa njerëz janë kapituj,\njo e gjithë historia.", FONT_SERIF_B, 58, 860),
    (30.6, 34.0, "Shëno dikë që duhet ta shohë këtë.", FONT_SANS_B, 40, 1500),
]


# ---------------------------------------------------------------- rain
N_DROPS = 420
drops = np.stack([rng.uniform(-200, W + 200, N_DROPS), rng.uniform(0, H, N_DROPS),
                  rng.uniform(1300, 2100, N_DROPS), rng.uniform(30, 70, N_DROPS)], 1)


def draw_rain(pil, t, intensity):
    d = ImageDraw.Draw(pil)
    n = int(N_DROPS * intensity)
    for x0, y0, v, ln in drops[:n]:
        y = (y0 + v * t) % (H + 100) - 100
        x = x0 - 0.12 * (y - y0)
        x = (x % (W + 200)) - 100
        c = 120 + int(ln)
        d.line((x, y, x - ln * 0.12, y + ln), fill=(c, c + 8, c + 30), width=2)


# ---------------------------------------------------------------- story state
def state(t):
    """Positions/poses of both characters at time t."""
    he = dict(x=486.0, facing=1, phase=0.0, bow=0.0, look=0.0)
    she = dict(x=594.0, facing=-1, phase=0.0, bow=0.0, look=0.0)
    hold = 1 - ramp(t, 10.9, 11.9)          # holding hands amount
    she["bow"] = ramp(t, 7.4, 8.4)          # she lowers her head at "nuk e di më"
    he["bow"] = ramp(t, 10.9, 12.0)
    if t >= 12.6:                            # turn away from each other
        he["facing"], she["facing"] = -1, 1
    vh, vs = 46.0, 36.0
    if t > 14.0:
        dh = vh * (t - 14.0)
        he["x"] -= dh
        he["phase"] = dh / 26.0
    ts = min(t, 22.0)
    if ts > 14.0:
        ds = vs * (ts - 14.0)
        she["x"] += ds
        she["phase"] = ds / 22.0
        if t >= 22.0:  # settle legs
            she["phase"] = round(she["phase"] / math.pi) * math.pi
    if t > 23.2:                             # she turns back to look at him
        she["facing"] = -1
        she["look"] = 1.0
    return he, she, hold


# ---------------------------------------------------------------- render
def main():
    bg = build_background()
    light = build_light()
    vig = build_vignette()
    heart_full, heart_l, heart_r = build_heart_halves()
    band_h = BAND_Y1 - BAND_Y0
    shadow_col = np.array([7, 6, 14], np.float32)
    heart_col = np.array([230, 30, 60], np.float32)

    write_music()

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", WAV,
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    n_frames = int(DURATION * FPS)
    for fi in range(n_frames):
        t = fi / FPS
        frame = bg.copy()

        # lamp flicker after the break-up
        flick = 1.0
        if 11.0 < t < 13.0:
            flick = 0.55 + 0.45 * (math.sin(t * 47) > -0.2)
        frame += light * flick

        # characters (supersampled mask in a band)
        he, she, hold = state(t)
        mask = Image.new("L", (W * SS, band_h * SS), 0)
        md = ImageDraw.Draw(mask)
        sh_y = (GROUND - BAND_Y0) - 430 + 2 * 430 * 0.075 + 10
        meet = ((he["x"] + she["x"]) / 2, sh_y + 150)
        draw_person(md, he["x"], he["facing"], he["phase"], False,
                    arm_target=(meet[0], meet[1], 1) if hold > 0.02 and he["facing"] == 1 else None,
                    bow=he["bow"])
        draw_person(md, she["x"], she["facing"], she["phase"], True,
                    arm_target=(meet[0], meet[1], -1) if hold > 0.02 and she["facing"] == -1 else None,
                    bow=she["bow"], look_back=she["look"])
        m = np.asarray(mask.resize((W, band_h), Image.LANCZOS), np.float32)[..., None] / 255.0

        # rim light on the figures from the lamp
        region = frame[BAND_Y0:BAND_Y1]
        frame[BAND_Y0:BAND_Y1] = region * (1 - m) + shadow_col * m
        # wet-street reflection
        refl = m[::-1][: H - GROUND - 10] * 0.35
        rh = refl.shape[0]
        frame[GROUND + 6:GROUND + 6 + rh] = frame[GROUND + 6:GROUND + 6 + rh] * (1 - refl) + shadow_col * refl

        # heart
        if t < 14.0:
            pil_heart_alpha = ramp(t, 4.0, 5.2)
            beat = 1 + 0.08 * max(0, math.sin(t * 2 * math.pi * 1.1)) ** 6
            cx, cy = 540, 1000
            if t < 10.8:
                parts = [(heart_full, 0, 0, 0, 1.0)]
            else:
                k = ramp(t, 10.8, 13.6)
                fade = 1 - ramp(t, 12.0, 13.8)
                parts = [(heart_l, -70 * k, 160 * k * k, 18 * k, fade),
                         (heart_r, 70 * k, 160 * k * k, -18 * k, fade)]
                beat = 1.0
            for img, dx, dy, rot, a in parts:
                hi = img
                if beat != 1.0:
                    s = int(img.width * beat)
                    hi = img.resize((s, s), Image.BILINEAR)
                if rot:
                    hi = hi.rotate(rot, resample=Image.BILINEAR)
                ha = np.asarray(hi, np.float32)[..., None] / 255.0 * a * pil_heart_alpha
                x0 = int(cx + dx - hi.width / 2)
                y0 = int(cy + dy - hi.height / 2)
                sub = frame[y0:y0 + hi.height, x0:x0 + hi.width]
                frame[y0:y0 + hi.height, x0:x0 + hi.width] = sub * (1 - ha) + heart_col * ha
                # glow
                frame[y0:y0 + hi.height, x0:x0 + hi.width] += heart_col * 0.15 * a * pil_heart_alpha

        frame *= vig

        # rain (gets heavier after the break-up)
        pil = Image.fromarray(frame.clip(0, 255).astype(np.uint8))
        draw_rain(pil, t, 0.35 + 0.65 * ramp(t, 10.8, 15.0))

        # slow cinematic camera: push in, then pull out to show the distance
        zoom = 1 + 0.10 * ramp(t, 3.5, 10.5) - 0.10 * ramp(t, 13.0, 21.0)
        if zoom > 1.001:
            cw, ch = W / zoom, H / zoom
            cxz, cyz = 540, 1180
            y0 = min(max(0, cyz - ch / 2), H - ch)
            box = (cxz - cw / 2, y0, cxz + cw / 2, y0 + ch)
            pil = pil.resize((W, H), Image.BICUBIC, box=box)
        frame = np.asarray(pil).astype(np.float32)

        # scene fades: from black at start, to black for the ending card
        scene_a = ramp(t, 3.0, 4.6) * (1 - ramp(t, 27.4, 28.6))
        frame *= scene_a

        # broken heart on the end card
        if t > 28.4:
            a = ramp(t, 28.6, 29.6)
            for img, dx in ((heart_l, -16), (heart_r, 16)):
                hi = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
                ha = np.asarray(hi, np.float32)[..., None] / 255.0 * a
                x0, y0 = int(540 + dx - hi.width / 2), 1140
                sub = frame[y0:y0 + hi.height, x0:x0 + hi.width]
                frame[y0:y0 + hi.height, x0:x0 + hi.width] = sub * (1 - ha) + heart_col * ha

        for start, end, text, font, size, y in CAPTIONS:
            if start - 0.05 <= t <= end + 0.05:
                box = font != FONT_SERIF_B and y > 1200
                frame = blend_text(frame, text_layer(text, font, size, y=y, box=box),
                                   fade_window(t, start, end))

        # film grain
        frame += rng.normal(0, 4, (H // 4, W // 4, 1)).repeat(4, 0).repeat(4, 1)

        ff.stdin.write(frame.clip(0, 255).astype(np.uint8).tobytes())
        if fi % 60 == 0:
            print(f"  kuadri {fi}/{n_frames}", flush=True)

    ff.stdin.close()
    ff.wait()
    os.remove(WAV)
    print("Gati:", OUT)


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


def write_music():
    total = int(DURATION * SR)
    out = np.zeros(total + SR * 4)

    def add(sig, at):
        i = int(at * SR)
        out[i:i + len(sig)] += sig[: len(out) - i]

    chords = [  # Am – F – C – G (melancholic)
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
        add(piano(note_freq(bass), 4.0, 0.55), t)
        for i in range(8):
            n = notes[[0, 1, 2, 3, 2, 1, 2, 3][i]]
            add(piano(note_freq(n), 2.0, 0.22), t + i * beat)
        if t >= 4.0:  # melody enters with the scene
            for i in range(8):
                m = melody[(bar * 8 + i) % len(melody)]
                if m:
                    add(piano(note_freq(m), 2.5, 0.30), t + i * beat)
        # soft string pad
        tt = np.arange(int(4.0 * SR)) / SR
        pad_env = np.sin(np.pi * tt / 4.0) ** 2 * (0.06 if t > 3 else 0.02)
        pad = sum(np.sin(2 * np.pi * note_freq(n) * tt) + 0.5 * np.sin(2 * np.pi * note_freq(n) * 1.003 * tt)
                  for n in notes[:3])
        add(pad * pad_env, t)
        t += 4 * 2 * beat
        bar += 1

    # low "heartbreak" impact
    tt = np.arange(int(2.5 * SR)) / SR
    boom = np.sin(2 * np.pi * (55 - 15 * tt) * tt) * np.exp(-tt * 2.0) * 0.9
    add(boom, 10.8)

    # simple reverb (feedback comb filters)
    dry = out.copy()
    for delay, g in ((0.0297, 0.6), (0.0371, 0.55), (0.0411, 0.5), (0.0437, 0.45)):
        dsm = int(delay * SR)
        y = dry.copy()
        for i in range(dsm, len(y), dsm):
            y[i:i + dsm] += g * y[i - dsm:i][: len(y[i:i + dsm])]
        out += y * 0.18

    out = out[:total]
    # rain noise, gets heavier after the break-up
    noise = rng.normal(0, 1, total)
    noise = np.convolve(noise, np.ones(8) / 8, mode="same")
    tl = np.arange(total) / SR
    rain_amt = 0.05 + 0.07 * np.clip((tl - 10.8) / 4, 0, 1)
    out = out / (np.abs(out).max() + 1e-9) * 0.8 + noise * rain_amt
    # fade in/out
    out *= np.clip(tl / 1.0, 0, 1) * np.clip((DURATION - tl) / 2.5, 0, 1)
    out = out / (np.abs(out).max() + 1e-9) * 0.9
    pcm = (out * 32767).astype(np.int16)
    stereo = np.stack([pcm, pcm], 1)
    with wave.open(WAV, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())


if __name__ == "__main__":
    main()
