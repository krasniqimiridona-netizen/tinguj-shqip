#!/usr/bin/env python3
"""Krijon 9 postimet e para (1080x1350) për Instagramin e Shqiponja Digital.

Përdorimi:
    python3 instagram/krijo_postimet.py     # krijon instagram/postimet/01.png ... 09.png
"""
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1350
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "postimet")
FONTS = "/usr/share/fonts/opentype/inter/"

NIGHT = (20, 14, 32)
ROSE = (255, 111, 159)
VIOLET = (155, 108, 255)
GOLD = (244, 199, 107)
TEXT = (241, 237, 248)
MUTED = (179, 169, 199)
PANEL = (34, 26, 52)


def font(weight, size):
    name = {"black": "InterDisplay-Black", "xbold": "InterDisplay-ExtraBold", "bold": "Inter-Bold",
            "semi": "Inter-SemiBold", "med": "Inter-Medium", "reg": "Inter-Regular"}[weight]
    return ImageFont.truetype(FONTS + name + ".otf", size)


def background(glow_x=0.8, glow_y=0.1):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    xx, yy = xx / W, yy / H
    bg = np.zeros((H, W, 3), np.float32) + np.array(NIGHT)
    bg += np.exp(-(((xx - glow_x) ** 2 + (yy - glow_y) ** 2) / 0.10))[..., None] * np.array(VIOLET) * 0.45
    bg += np.exp(-(((xx - (1 - glow_x)) ** 2 + (yy - 0.98) ** 2) / 0.08))[..., None] * np.array([224, 36, 94]) * 0.35
    return Image.fromarray(bg.clip(0, 255).astype(np.uint8))


def wrap(draw, text, fnt, width):
    lines = []
    for para in text.split("\n"):
        words, cur = para.split(" "), ""
        for w in words:
            test = (cur + " " + w).strip()
            if draw.textlength(test, font=fnt) <= width:
                cur = test
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def text_block(draw, xy, text, fnt, fill, width, spacing=1.18):
    x, y = xy
    for line in wrap(draw, text, fnt, width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += int(fnt.size * spacing)
    return y


def footer(img, label="Shqiponja Digital"):
    d = ImageDraw.Draw(img)
    logo = Image.open(os.path.join(HERE, "logo-C-libri.png")).resize((64, 64), Image.LANCZOS)
    mask = Image.new("L", (64, 64), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 63, 63), fill=255)
    img.paste(logo, (80, H - 120), mask)
    d.text((160, H - 104), label, font=font("bold", 30), fill=TEXT)


def eyebrow(d, y, text, color=ROSE):
    d.text((80, y), text.upper(), font=font("bold", 28), fill=color)


def numbered(d, y, n, title, body, accent=ROSE, width=820):
    d.ellipse((80, y, 140, y + 60), fill=accent)
    f = font("xbold", 32)
    d.text((110, y + 30), str(n), font=f, fill=NIGHT, anchor="mm")
    y2 = text_block(d, (170, y + 4), title, font("bold", 40), TEXT, width)
    if body:
        y2 = text_block(d, (170, y2 + 6), body, font("reg", 31), MUTED, width, 1.3)
    return y2 + 34


def post_01():
    img = background()
    d = ImageDraw.Draw(img)
    eyebrow(d, 150, "Mirë se erdhe")
    y = text_block(d, (80, 210), "Mëso të fitosh para online.", font("black", 112), TEXT, 900, 1.05)
    y = text_block(d, (80, y + 10), "Pa mashtrime.", font("black", 112), ROSE, 900, 1.05)
    y = text_block(d, (80, y + 50),
                   "Këshilla të sinqerta çdo ditë: freelancing, Instagram, produkte digjitale dhe si të marrësh klientin e parë.",
                   font("med", 38), MUTED, 880, 1.35)
    d.rounded_rectangle((80, y + 50, 560, y + 140), radius=45, fill=ROSE)
    d.text((320, y + 95), "Ndiqe faqen", font=font("bold", 38), fill=NIGHT, anchor="mm")
    footer(img)
    return img


def post_02():
    img = background(0.2, 0.15)
    d = ImageDraw.Draw(img)
    eyebrow(d, 110, "Libri i ri")
    text_block(d, (80, 160), "Fito Online", font("black", 104), TEXT, 900)
    text_block(d, (80, 290), "12 mënyra reale për të fituar para nga interneti", font("med", 38), MUTED, 900, 1.3)
    cover = Image.open(os.path.join(HERE, "..", "ebook", "kopertina.png")).convert("RGB")
    cw = 470
    cover = cover.resize((cw, int(cover.height * cw / cover.width)), Image.LANCZOS)
    shadow = Image.new("L", (cover.width + 120, cover.height + 120), 0)
    ImageDraw.Draw(shadow).rounded_rectangle((60, 70, cover.width + 60, cover.height + 70), 16, fill=200)
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))
    cx, cy = (W - cover.width) // 2, 420
    img.paste((0, 0, 0), (cx - 60, cy - 60), shadow)
    img.paste(cover, (cx, cy))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((80, H - 230, W - 80, H - 150), radius=40, fill=ROSE)
    d.text((W / 2, H - 190), "7€  ·  PDF 31 faqe  ·  Linku në bio", font=font("bold", 34), fill=NIGHT, anchor="mm")
    footer(img)
    return img


def post_03():
    img = background()
    d = ImageDraw.Draw(img)
    eyebrow(d, 110, "Kujdes")
    y = text_block(d, (80, 160), "3 mashtrime online që duhet t'i njohësh", font("black", 80), TEXT, 920, 1.08)
    y += 50
    items = [
        ("Të kërkojnë para për të të dhënë punë", "Punëdhënësi i vërtetë të paguan ty, jo e kundërta."),
        ("\"100€ në ditë pa eksperiencë\"", "Premtimet e tepërta janë shenja e parë e mashtrimit."),
        ("\"Kliko reklama dhe fito\"", "Paguajnë centë, ose nuk paguajnë fare kur arrin te tërheqja."),
    ]
    for i, (t, b) in enumerate(items, 1):
        y = numbered(d, y, i, t, b, ROSE)
    text_block(d, (80, y + 10), "Edhe 4 të tjera janë te libri \"Fito Online\".", font("semi", 32), GOLD, 900)
    footer(img)
    return img


def post_04():
    img = background(0.15, 0.1)
    d = ImageDraw.Draw(img)
    eyebrow(d, 110, "Ide për të filluar", GOLD)
    y = text_block(d, (80, 160), "12 mënyra për të fituar online", font("black", 84), TEXT, 920, 1.08)
    items = ["Freelancing", "Menaxhim rrjetesh sociale", "Krijim përmbajtjeje", "Video UGC për marka",
             "Produkte digjitale", "Mësimdhënie online", "Përkthime", "Marketing me afiliim",
             "Dizajn dhe montim", "Shitje online lokale", "Print-on-demand", "Shërbime me AI"]
    y += 50
    col_w = 460
    for i, it in enumerate(items):
        col, row = i % 2, i // 2
        x = 80 + col * col_w
        yy = y + row * 92
        d.rounded_rectangle((x, yy, x + col_w - 30, yy + 72), radius=20, fill=PANEL)
        d.text((x + 24, yy + 36), f"{i + 1:02d}", font=font("xbold", 28), fill=ROSE, anchor="lm")
        d.text((x + 84, yy + 36), it, font=font("semi", 28), fill=TEXT, anchor="lm")
    footer(img)
    return img


def quote_post(line1, line2, sub):
    img = background(0.5, 0.0)
    d = ImageDraw.Draw(img)
    d.text((80, 260), "“", font=font("black", 260), fill=ROSE)
    y = text_block(d, (80, 470), line1, font("black", 96), TEXT, 920, 1.08)
    y = text_block(d, (80, y), line2, font("black", 96), ROSE, 920, 1.08)
    text_block(d, (80, y + 50), sub, font("med", 36), MUTED, 880, 1.35)
    footer(img)
    return img


def post_05():
    return quote_post("Fillo sot.", "Jo të hënën.",
                      "Dallimi mes atyre që fitojnë online dhe atyre që vetëm ëndërrojnë nuk është talenti. Është që të parët filluan.")


def post_06():
    img = background(0.85, 0.2)
    d = ImageDraw.Draw(img)
    eyebrow(d, 110, "A e dije?", GOLD)
    y = text_block(d, (80, 160), "Gjuha shqipe mund të të sjellë para.", font("black", 86), TEXT, 920, 1.08)
    y = text_block(d, (80, y + 40),
                   "Prindërit e diasporës në Gjermani, Zvicër dhe Itali kërkojnë mësues shqipeje online për fëmijët e tyre.",
                   font("med", 38), MUTED, 900, 1.35)
    y += 40
    for i, (t, b) in enumerate([("Krijo profil", "Preply, italki ose grupet e diasporës në Facebook"),
                                ("Mësimi i parë me ulje", "Për të marrë vlerësimet e para"),
                                ("Paketë mujore", "8 orë në muaj = të ardhura të qëndrueshme")], 1):
        y = numbered(d, y, i, t, b, GOLD)
    footer(img)
    return img


def post_07():
    img = background(0.2, 0.05)
    d = ImageDraw.Draw(img)
    eyebrow(d, 110, "Ruaje për më vonë")
    y = text_block(d, (80, 160), "Plani 30-ditor", font("black", 96), TEXT, 920)
    y += 40
    weeks = [("Java 1", "Zgjidh një aftësi dhe hap mënyrën e pagesës"),
             ("Java 2", "Bëj 3 shembuj pune dhe posto çdo ditë"),
             ("Java 3", "Dërgo 5–10 mesazhe klientëve çdo ditë"),
             ("Java 4", "Kryej punën e parë dhe kërko vlerësim")]
    for wk, txt in weeks:
        d.rounded_rectangle((80, y, W - 80, y + 160), radius=28, fill=PANEL)
        d.text((120, y + 30), wk, font=font("xbold", 36), fill=VIOLET)
        text_block(d, (120, y + 80), txt, font("med", 32), TEXT, 820)
        y += 190
    footer(img)
    return img


def post_08():
    img = background(0.8, 0.1)
    d = ImageDraw.Draw(img)
    eyebrow(d, 110, "Shabllon falas")
    y = text_block(d, (80, 160), "Mesazhi që të sjell klientin e parë", font("black", 80), TEXT, 920, 1.08)
    y += 40
    box_h = 470
    d.rounded_rectangle((80, y, W - 80, y + box_h), radius=28, fill=(14, 10, 24), outline=(60, 48, 90), width=2)
    msg = ("Përshëndetje [Emri]!\n\n"
           "Ndjek [biznesin] prej kohësh dhe më pëlqen shumë [diçka specifike].\n\n"
           "Ju bëra 3 postime shembull falas. Nëse ju pëlqejnë, mund t'jua bëj çdo muaj. "
           "Nëse jo, mbajini si dhuratë.")
    text_block(d, (120, y + 40), msg, font("med", 33), TEXT, 830, 1.38)
    text_block(d, (80, y + box_h + 30), "Ruaje dhe dërgoja sot 5 bizneseve në qytetin tënd.", font("semi", 32), GOLD, 900)
    footer(img)
    return img


def post_09():
    return quote_post("Interneti nuk është makinë parash.", "Është treg.",
                      "Kush ofron vlerë, fiton. Fillo me një aftësi që e ke sot.")


def main():
    os.makedirs(OUT, exist_ok=True)
    posts = [post_01, post_02, post_03, post_04, post_05, post_06, post_07, post_08, post_09]
    for i, fn in enumerate(posts, 1):
        fn().save(os.path.join(OUT, f"{i:02d}.png"))
    print("Gati:", OUT)


if __name__ == "__main__":
    main()
