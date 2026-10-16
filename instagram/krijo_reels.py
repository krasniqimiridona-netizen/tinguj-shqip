#!/usr/bin/env python3
"""Krijon 5 Reels të animuar (1080x1920, 30 fps, me muzikë) për @fitoonline.shqip.

Përdorimi:
    python3 instagram/krijo_reels.py          # krijon instagram/reels/*.mp4
    python3 instagram/krijo_reels.py 3        # vetëm reel-in nr. 3
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, SR = 1080, 1920, 30, 44100
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "reels")
FONTS = "/usr/share/fonts/opentype/inter/"
HANDLE = "@fitoonline.shqip"

NIGHT = (20, 14, 32)
ROSE = (255, 111, 159)
VIOLET = (155, 108, 255)
GOLD = (244, 199, 107)
TEXT = (241, 237, 248)
MUTED = (179, 169, 199)
PANEL = (34, 26, 52)

# Instagram covers the bottom ~380px and the right edge with its UI: keep content inside this box.
X0, X1, Y_TOP = 80, 940, 260

_fonts = {}


def font(weight, size):
    key = (weight, size)
    if key not in _fonts:
        name = {"black": "InterDisplay-Black", "xbold": "InterDisplay-ExtraBold", "bold": "Inter-Bold",
                "semi": "Inter-SemiBold", "med": "Inter-Medium"}[weight]
        _fonts[key] = ImageFont.truetype(FONTS + name + ".otf", size)
    return _fonts[key]


def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def wrap(text, fnt, width):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    lines, cur = [], ""
    for w in text.split(" "):
        test = (cur + " " + w).strip()
        if d.textlength(test, font=fnt) <= width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


# ---------------------------------------------------------------- background
_yy, _xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
_yy, _xx = _yy / (H // 4), _xx / (W // 4)


def background(t):
    gx1, gy1 = 0.75 + 0.08 * math.sin(t * 0.5), 0.12 + 0.04 * math.cos(t * 0.4)
    gx2, gy2 = 0.2 + 0.08 * math.cos(t * 0.45), 0.92 + 0.03 * math.sin(t * 0.6)
    bg = np.zeros((H // 4, W // 4, 3), np.float32) + np.array(NIGHT)
    bg += np.exp(-(((_xx - gx1) ** 2) / 0.12 + ((_yy - gy1) ** 2) / 0.05))[..., None] * np.array(VIOLET) * 0.5
    bg += np.exp(-(((_xx - gx2) ** 2) / 0.10 + ((_yy - gy2) ** 2) / 0.04))[..., None] * np.array([224, 36, 94]) * 0.4
    return Image.fromarray(bg.clip(0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR).convert("RGBA")


# ---------------------------------------------------------------- scene drawing
def rgba(col, a):
    return col + (int(255 * max(0.0, min(1.0, a))),)


def draw_lines(d, lines, y, a, dy):
    """lines: [(text, font, color)] drawn left-aligned, returns y after."""
    for text, fnt, col in lines:
        d.text((X0, y + dy), text, font=fnt, fill=rgba(col, a))
        y += int(fnt.size * 1.12)
    return y


def title_lines(parts, size):
    out = []
    for text, col in parts:
        for ln in wrap(text, font("black", size), X1 - X0):
            out.append((ln, font("black", size), col))
    return out


def scene_hook(d, t, dur, s):
    fade = 1 - ease((t - (dur - 0.3)) / 0.3)
    y = 560
    if s.get("eyebrow"):
        a = ease(t / 0.3) * fade
        d.text((X0, y - 80), s["eyebrow"].upper(), font=font("bold", 36), fill=rgba(ROSE, a))
    for i, (text, col) in enumerate(s["title"]):
        a = ease((t - 0.15 - i * 0.35) / 0.4) * fade
        lines = title_lines([(text, col)], s.get("size", 100))
        y = draw_lines(d, lines, y, a, (1 - a) * 50)


def scene_list(d, t, dur, s):
    fade = 1 - ease((t - (dur - 0.3)) / 0.3)
    y = 470
    if s.get("heading"):
        a = ease(t / 0.3) * fade
        y = draw_lines(d, title_lines([(s["heading"], TEXT)], 76), y, a, 0) + 50
    step = s.get("step", 1.6)
    for i, item in enumerate(s["items"]):
        title, sub = item if isinstance(item, tuple) else (item, None)
        a = ease((t - 0.3 - i * step) / 0.35) * fade
        dx = (1 - a) * 60
        accent = s.get("accent", ROSE)
        label = s["labels"][i] if s.get("labels") else str(i + 1)
        if a > 0:
            if len(label) <= 2:
                d.ellipse((X0 + dx, y, X0 + 76 + dx, y + 76), fill=rgba(accent, a))
                d.text((X0 + 38 + dx, y + 38), label, font=font("xbold", 40), fill=rgba(NIGHT, a), anchor="mm")
                tx = X0 + 104
            else:
                d.text((X0 + dx, y + 8), label, font=font("xbold", 44), fill=rgba(accent, a))
                tx = X0 + 200
        else:
            tx = X0 + (104 if len(label) <= 2 else 200)
        ty = y + 6
        for ln in wrap(title, font("bold", 56), X1 - tx):
            d.text((tx + dx, ty), ln, font=font("bold", 56), fill=rgba(TEXT, a))
            ty += 68
        if sub:
            for ln in wrap(sub, font("med", 42), X1 - tx):
                d.text((tx + dx, ty + 4), ln, font=font("med", 42), fill=rgba(MUTED, a))
                ty += 54
        y = max(ty, y + 80) + 64


_logo = None
_cover = None


def scene_end(img, d, t, dur, s):
    global _logo, _cover
    a = ease(t / 0.4)
    if s.get("cover"):
        if _cover is None:
            c = Image.open(os.path.join(HERE, "..", "ebook", "kopertina.png")).convert("RGBA")
            _cover = c.resize((440, int(c.height * 440 / c.width)), Image.LANCZOS)
        cov = _cover.copy()
        cov.putalpha(int(255 * a))
        img.alpha_composite(cov, ((W - cov.width) // 2, int(300 + (1 - a) * 80)))
        y = 300 + cov.height + 50
    else:
        if _logo is None:
            lg = Image.open(os.path.join(HERE, "logo-C-libri.png")).convert("RGBA").resize((300, 300), Image.LANCZOS)
            m = Image.new("L", (300, 300), 0)
            ImageDraw.Draw(m).ellipse((0, 0, 299, 299), fill=255)
            lg.putalpha(m)
            _logo = lg
        sc = 0.6 + 0.4 * ease(t / 0.5)
        lg = _logo.resize((int(300 * sc), int(300 * sc)), Image.LANCZOS)
        al = lg.getchannel("A").point(lambda v: int(v * a))
        lg.putalpha(al)
        img.alpha_composite(lg, ((W - lg.width) // 2, 420 + (300 - lg.height) // 2))
        y = 800
    for i, (text, col, size) in enumerate(s["lines"]):
        aa = ease((t - 0.25 - i * 0.25) / 0.35)
        d.text((W // 2, y + (1 - aa) * 30), text, font=font("black", size), fill=rgba(col, aa), anchor="ma")
        y += int(size * 1.15)
    y += 50
    ap = ease((t - 0.9) / 0.35)
    pulse = 1 + 0.03 * math.sin(t * 6)
    bw, bh = 560 * pulse, 110 * pulse
    d.rounded_rectangle((W / 2 - bw / 2, y, W / 2 + bw / 2, y + bh), radius=bh / 2, fill=rgba(ROSE, ap))
    d.text((W / 2, y + bh / 2), "Linku në bio", font=font("xbold", 52), fill=rgba(NIGHT, ap), anchor="mm")
    d.text((W / 2, y + bh + 50), HANDLE, font=font("bold", 40), fill=rgba(TEXT, ap), anchor="ma")


def render_frame(t, scenes, total):
    img = background(t)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    start = 0.0
    for s in scenes:
        if start <= t < start + s["dur"] or (s is scenes[-1] and t >= start):
            lt = t - start
            if s["type"] == "hook":
                scene_hook(d, lt, s["dur"], s)
            elif s["type"] == "list":
                scene_list(d, lt, s["dur"], s)
            else:
                img.alpha_composite(layer)
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                d = ImageDraw.Draw(layer)
                scene_end(img, d, lt, s["dur"], s)
            break
        start += s["dur"]
    # progress bar + handle tag at the top
    d.rounded_rectangle((X0, 150, W - X0, 158), radius=4, fill=(255, 255, 255, 40))
    d.rounded_rectangle((X0, 150, X0 + (W - 2 * X0) * min(1, t / total), 158), radius=4, fill=ROSE + (255,))
    d.text((X0, 180), HANDLE, font=font("semi", 30), fill=MUTED + (255,))
    img.alpha_composite(layer)
    return img.convert("RGB")


# ---------------------------------------------------------------- music
def music(path, dur, seed):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros(n + SR)
    bpm = 96
    beat = 60 / bpm
    t = np.arange(int(0.5 * SR)) / SR

    def add(sig, at, g=1.0):
        i = int(at * SR)
        out[i:i + len(sig)] += sig[: len(out) - i] * g

    kick = np.sin(2 * np.pi * (110 * np.exp(-t * 18) + 45) * t) * np.exp(-t * 9)
    hat = rng.normal(0, 1, int(0.06 * SR)) * np.exp(-np.arange(int(0.06 * SR)) / SR * 70)
    hat = np.diff(hat, prepend=0)

    def note(f, d=1.2, v=0.25):
        tt = np.arange(int(d * SR)) / SR
        env = np.exp(-tt * 2.5) * np.minimum(1, tt / 0.01)
        return (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * env * v

    chords = [[220, 261.6, 329.6], [174.6, 220, 261.6], [261.6, 329.6, 392], [196, 246.9, 293.7]]
    b, k = 0.0, 0
    while b < dur:
        add(kick, b, 0.9 if k % 4 in (0, 2) else 0.0)
        add(hat, b + beat / 2, 0.25)
        if k % 4 == 0:
            for f in chords[(k // 4) % 4]:
                add(note(f, 2.4, 0.18), b)
        mel = chords[(k // 4) % 4][k % 3] * 2
        add(note(mel, 0.6, 0.10), b + beat / 2)
        b += beat
        k += 1
    out = out[:n]
    tl = np.arange(n) / SR
    out *= np.clip(tl / 0.3, 0, 1) * np.clip((dur - tl) / 1.2, 0, 1)
    out = out / (np.abs(out).max() + 1e-9) * 0.8
    pcm = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(np.stack([pcm, pcm], 1).tobytes())


# ---------------------------------------------------------------- the 5 reels
END_BOOK = lambda pre: {"type": "end", "dur": 4.0, "lines": [(pre, MUTED, 52), ("Fito Online", ROSE, 110)]}

REELS = [
    ("reel-1-mashtrimet", [
        {"type": "hook", "dur": 2.6, "eyebrow": "Kujdes",
         "title": [("3 mashtrime online", TEXT), ("që duhet t'i dish", ROSE)]},
        {"type": "list", "dur": 7.4, "step": 2.0, "items": [
            ("Të kërkojnë para për të të dhënë punë", "Punëdhënësi i vërtetë të paguan ty."),
            ("\"100€ në ditë pa eksperiencë\"", "Premtimet e tepërta janë shenja e parë."),
            ("\"Kliko reklama dhe fito\"", "Paguajnë centë, ose asgjë."),
        ]},
        END_BOOK("Edhe 4 të tjera te libri"),
    ]),
    ("reel-2-bizneset", [
        {"type": "hook", "dur": 2.6, "eyebrow": "Ide për para",
         "title": [("Bizneset në qytetin tënd", TEXT), ("kanë nevojë për ty.", ROSE)]},
        {"type": "list", "dur": 7.4, "step": 2.0, "accent": GOLD, "items": [
            ("Duan Reels, por s'kanë kohë", "Restorante, sallone, dyqane."),
            ("Ti ua bën me telefon", "CapCut dhe Canva mjaftojnë."),
            ("Ofro paketë mujore", "P.sh. 12 postime + 4 Reels në muaj."),
        ]},
        END_BOOK("Mesazhin që u dërgon e gjen te"),
    ]),
    ("reel-3-libri", [
        {"type": "hook", "dur": 3.2, "eyebrow": "Doli libri",
         "title": [("12 mënyra reale", TEXT), ("për të fituar online.", TEXT), ("Pa gënjeshtra.", ROSE)], "size": 104},
        {"type": "list", "dur": 5.4, "step": 1.1, "heading": "Brenda gjen:", "items": [
            "12 mënyra me hapa të qartë", "Shabllone mesazhesh gati", "Mashtrimet që duhet shmangur",
            "Plan 30-ditor"]},
        {"type": "end", "dur": 4.4, "cover": True, "lines": [("Fito Online · 7€", TEXT, 72)]},
    ]),
    ("reel-4-gjuha-shqipe", [
        {"type": "hook", "dur": 2.8, "eyebrow": "A e dije?",
         "title": [("Gjuha shqipe", TEXT), ("mund të të sjellë para.", ROSE)]},
        {"type": "list", "dur": 7.2, "step": 2.0, "accent": GOLD, "items": [
            ("Prindërit në diasporë kërkojnë mësues shqipeje", "Gjermani, Zvicër, Itali…"),
            ("Jep mësim online nga shtëpia", "Preply, italki, grupet në Facebook."),
            ("Ofro paketë mujore", "Të ardhura të qëndrueshme çdo muaj."),
        ]},
        END_BOOK("1 nga 12 mënyrat te"),
    ]),
    ("reel-5-plani-30-ditor", [
        {"type": "hook", "dur": 2.6, "eyebrow": "Ruaje këtë",
         "title": [("Do të fitosh online?", TEXT), ("Bëj këtë 30 ditë:", ROSE)]},
        {"type": "list", "dur": 7.6, "step": 1.6, "accent": VIOLET, "labels": ["J1", "J2", "J3", "J4"], "items": [
            ("Zgjidh një aftësi", "Dhe hap mënyrën e pagesës."),
            ("Bëj 3 shembuj pune", "Posto çdo ditë."),
            ("10 mesazhe në ditë", "Biznese, krijues, prindër."),
            ("Klienti i parë", "Kërko vlerësim dhe rekomandim."),
        ]},
        END_BOOK("Plani i plotë te"),
    ]),
]


def build(idx):
    name, scenes = REELS[idx]
    total = sum(s["dur"] for s in scenes)
    os.makedirs(OUT, exist_ok=True)
    wav = os.path.join(OUT, f"_{name}.wav")
    mp4 = os.path.join(OUT, f"{name}.mp4")
    music(wav, total, idx + 1)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", mp4]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(int(total * FPS)):
        ff.stdin.write(render_frame(fi / FPS, scenes, total).tobytes())
    ff.stdin.close()
    ff.wait()
    os.remove(wav)
    print("Gati:", mp4, f"({total:.0f}s)")


if __name__ == "__main__":
    which = [int(a) - 1 for a in sys.argv[1:]] or range(len(REELS))
    for i in which:
        build(i)
