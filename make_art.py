"""Nexus images for the Narrator: a 16:9 header and a 'how it works' card."""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "art")
F = r"C:\Windows\Fonts"
GOLD = (214, 178, 108)
PALE = (232, 222, 200)
DIM = (160, 146, 120)


def font(name, size):
    return ImageFont.truetype(os.path.join(F, name), size)


def backdrop(w, h, seed=7):
    """Candle-lit hall: deep ember glow low in the middle, dark walls, grain."""
    img = Image.new("RGB", (w, h))
    px = img.load()
    cx, cy = w * 0.5, h * 0.62
    for y in range(h):
        for x in range(0, w):
            d = math.hypot((x - cx) / w, (y - cy) / h * 1.4)
            glow = max(0.0, 1.0 - d * 1.9)
            r = int(14 + 96 * glow ** 1.6)
            g = int(10 + 44 * glow ** 1.9)
            b = int(9 + 18 * glow ** 2.2)
            px[x, y] = (r, g, b)
    rnd = random.Random(seed)
    grain = Image.effect_noise((w, h), 22).convert("RGB")
    img = Image.blend(img, grain, 0.05)
    # drifting embers
    d = ImageDraw.Draw(img, "RGBA")
    for _ in range(140):
        x, y = rnd.uniform(0, w), rnd.uniform(h * 0.2, h)
        s = rnd.uniform(1, 3.2)
        a = int(rnd.uniform(40, 150))
        d.ellipse((x - s, y - s, x + s, y + s), fill=(255, 170, 80, a))
    return img.filter(ImageFilter.GaussianBlur(0.6))


def waveform(draw, cx, cy, width, height, bars=73, seed=3):
    rnd = random.Random(seed)
    step = width / bars
    for i in range(bars):
        t = i / (bars - 1)
        env = math.sin(math.pi * t) ** 0.8
        v = env * (0.35 + 0.65 * abs(math.sin(t * 19.0 + rnd.uniform(-0.6, 0.6))))
        bh = max(4, v * height)
        x = cx - width / 2 + i * step
        a = int(110 + 140 * env)
        draw.rounded_rectangle((x, cy - bh / 2, x + step * 0.5, cy + bh / 2),
                               radius=step * 0.25, fill=GOLD + (a,))


def centered(draw, y, text, f, fill, w, spacing=0):
    if spacing:
        widths = [draw.textlength(c, font=f) for c in text]
        total = sum(widths) + spacing * (len(text) - 1)
        x = (w - total) / 2
        for c, cw in zip(text, widths):
            draw.text((x, y), c, font=f, fill=fill)
            x += cw + spacing
    else:
        tw = draw.textlength(text, font=f)
        draw.text(((w - tw) / 2, y), text, font=f, fill=fill)


def rule(draw, cx, y, half, fill):
    draw.line((cx - half, y, cx - 14, y), fill=fill, width=2)
    draw.line((cx + 14, y, cx + half, y), fill=fill, width=2)
    draw.polygon([(cx, y - 7), (cx + 7, y), (cx, y + 7), (cx - 7, y)], fill=fill)


def header():
    w, h = 1920, 1080
    img = backdrop(w, h)
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    waveform(gd, w / 2, 735, 1180, 210)
    img.paste(glow.filter(ImageFilter.GaussianBlur(14)), (0, 0), glow.filter(ImageFilter.GaussianBlur(14)))
    img.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(img, "RGBA")
    centered(d, 250, "NARRATOR", font("georgiab.ttf", 190), PALE, w, spacing=26)
    rule(d, w / 2, 500, 330, GOLD + (220,))
    centered(d, 530, "Every voice in the hall, read aloud", font("georgiai.ttf", 54), GOLD, w)
    centered(d, 900, "for AI Influence 7.0   \u00b7   Mount & Blade II: Bannerlord",
             font("georgia.ttf", 40), DIM, w)
    img.save(os.path.join(OUT, "narrator_header.png"), optimize=True)


def how_it_works():
    w, h = 1920, 1080
    img = backdrop(w, h, seed=11)
    d = ImageDraw.Draw(img, "RGBA")
    centered(d, 90, "HOW IT SOUNDS", font("georgiab.ttf", 84), PALE, w, spacing=10)
    rule(d, w / 2, 215, 260, GOLD + (220,))
    rows = [
        ("A voice for everyone", "Each character keeps one voice, performed with the note the mod writes for every line."),
        ("A narrator for the actions", "Gestures and deeds are read by a steady narrator voice between the words."),
        ("Keeps up with the room", "Group scenes are voiced the moment a speaker starts, never a whole line behind."),
        ("Westeros, said right", "Daenerys, Braavos, Targaryen and more built in. Add your own in one line."),
        ("Your world, read on request", "Hotkeys for the day's events, your letters and the Memory Book."),
    ]
    tf, bf = font("georgiab.ttf", 46), font("georgia.ttf", 34)
    y = 290
    for title, body in rows:
        d.ellipse((300, y + 16, 316, y + 32), fill=GOLD)
        d.text((350, y), title, font=tf, fill=PALE)
        d.text((350, y + 62), body, font=bf, fill=DIM)
        y += 148
    img.save(os.path.join(OUT, "narrator_how_it_sounds.png"), optimize=True)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    header()
    how_it_works()
    print("art written to", OUT)
