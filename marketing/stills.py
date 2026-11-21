#!/usr/bin/env python3
"""Covers, YouTube thumbnail and carousel slides for the Aftergrid social kit, built from real footage frames."""
import json, os
from PIL import Image, ImageDraw, ImageFilter
from kit import (BG, CARD, LINE, TXT, DIM, ACC, SLATE, F_HEAD, F_BOLD, F_SEMI, F_XB, CTA, FOOT, OUT,
                 font, grid_bg, wordmark, draw_rich, pill, mix, mark)

def last(form, clip, idx=-1):
    m = json.load(open(f"{FOOT}/{form}/{clip}/manifest.json"))
    return Image.open(f"{FOOT}/{form}/{clip}/{m[idx]['f']}").convert("RGB")

def phone(im, shot, x, y, w, crop_h=None, tilt=0):
    """Real screenshot in a phone-shaped card with a soft shadow."""
    s = shot if crop_h is None else shot.crop((0, 0, shot.width, crop_h))
    h = int(w * s.height / s.width); s = s.resize((w, h), Image.LANCZOS)
    pad = int(w * .035)
    card = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([0, 0, w + pad * 2 - 1, h + pad * 2 - 1], radius=pad * 2.4, fill="#0b0d0f", outline="#3a444c", width=3)
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w, h], radius=pad * 1.6, fill=255)
    card.paste(s, (pad, pad), m)
    if tilt: card = card.rotate(tilt, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 170), (x + 10, y + 30), card.getchannel("A"))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(28)))
    im.alpha_composite(card, (x, y))
    return card.size

def save(im, name):
    os.makedirs(f"{OUT}/stills", exist_ok=True); im.convert("RGB").save(f"{OUT}/stills/{name}.png", optimize=True); print(name)

T = 9  # draw_rich time well past its animation = fully shown

def cover(name, lines, sub, shot, crop_h):
    W, H = 1080, 1920
    im = grid_bg(W, H, 0, glow=.9); d = ImageDraw.Draw(im)
    f = font(F_HEAD, 128); y = 300
    for i, ln in enumerate(lines):
        ff = f if f.getlength(ln) < W * .88 else font(F_HEAD, 128 * W * .88 / f.getlength(ln))
        d.text((W / 2, y), ln, font=ff, anchor="ma", fill=ACC if i == len(lines) - 1 else TXT); y += 140
    draw_rich(im, sub, font(F_SEMI, 46), W / 2, y + 20, W * .8, T, anchor="m", color=DIM)
    top = y + 130; pw = int(min(660, (1700 - top) * 1080 / crop_h * .93))
    phone(im, shot, (W - pw) // 2 - 20, top, pw, crop_h)
    wordmark(ImageDraw.Draw(im), W / 2, 1760, 40, anchor="m")
    save(im, name)

def thumb():
    W, H = 1280, 720
    im = grid_bg(W, H, 0, glow=.8); d = ImageDraw.Draw(im)
    f = font(F_HEAD, 92)
    for i, (ln, c) in enumerate([("GRID DOWN?", TXT), ("IT STILL", TXT), ("ANSWERS.", ACC)]):
        d.text((60, 120 + i * 104), ln, font=f, fill=c)
    pill(d, 62, 465, "NO INTERNET  ·  ONE USB STICK", font(F_XB, 30))
    wordmark(d, 62, 600, 34)
    phone(im, last("phone", "tourniquet"), 800, 40, 400, 1500, tilt=-4)
    save(im, "youtube-thumbnail")

def slide(n, build):
    W, H = 1080, 1350
    im = grid_bg(W, H, 0, glow=.7); d = ImageDraw.Draw(im)
    build(im, d, W, H)
    wordmark(d, 60, H - 92, 30)
    d.text((W - 60, H - 96), f"{n}/5", font=font(F_BOLD, 34), anchor="ra", fill=DIM)
    save(im, f"carousel-0{n}")

def s1(im, d, W, H):
    f = font(F_HEAD, 120)
    for i, (ln, c) in enumerate([("THE GRID", TXT), ("IS DOWN.", ACC)]): d.text((60, 260 + i * 132), ln, font=f, fill=c)
    draw_rich(im, "Your phone still turns on. *There's nothing to search.*", font(F_BOLD, 64), 60, 600, W - 120, T, lh=1.15)
    draw_rich(im, "Swipe: what you'd have instead →", font(F_SEMI, 42), 60, 1000, W - 120, T, color=DIM)
def s2(im, d, W, H):
    d.text((60, 120), "WHAT'S ON THE STICK", font=font(F_HEAD, 64), fill=ACC)
    rows = [("Medical", "Full medical encyclopedia (MDWiki) + Army first aid and field medicine manuals"),
            ("Survival", "US Army survival manuals, fallout protection, knots"),
            ("Water & food", "Purifying, storing, preserving, growing"),
            ("Fix & build", "Repair guides, solar, batteries, appropriate tech"),
            ("Maps", "Street maps that work with no signal"),
            ("Offline AI", "Ask in plain words; it answers from the library and shows sources")]
    y = 260
    for t, s in rows:
        d.rounded_rectangle([60, y, W - 60, y + 136], radius=18, fill=CARD, outline=LINE)
        d.rectangle([60, y + 20, 68, y + 116], fill=ACC)
        d.text((96, y + 18), t, font=font(F_HEAD, 40), fill=TXT)
        draw_rich(im, s, font(F_SEMI, 30), 96, y + 72, W - 200, T, color=DIM)
        y += 152
def s3(im, d, W, H):
    d.text((60, 100), "A REAL SEARCH.", font=font(F_HEAD, 70), fill=TXT)
    d.text((60, 185), "NO INTERNET.", font=font(F_HEAD, 70), fill=ACC)
    phone(im, last("phone", "tourniquet"), 250, 300, 580, 1500)
def s4(im, d, W, H):
    d.text((60, 100), "ASK LIKE A PERSON.", font=font(F_HEAD, 66), fill=TXT)
    d.text((60, 182), "IT SHOWS ITS SOURCES.", font=font(F_HEAD, 66), fill=ACC)
    phone(im, last("phone", "askwater", 92), 250, 300, 580, 1500)
def s5(im, d, W, H):
    d.text((60, 140), "HOW IT WORKS", font=font(F_HEAD, 72), fill=ACC)
    for i, s in enumerate(["Plug the USB into a PC", "Boot *Aftergrid*", "Everything works *offline*", "Phones join its *Wi-Fi*"]):
        y = 300 + i * 150; fz = font(F_HEAD, 56)
        d.rounded_rectangle([60, y, 140, y + 80], radius=16, fill=ACC)
        d.text((100, y + 40), str(i + 1), font=fz, anchor="mm", fill=BG)
        draw_rich(im, s, font(F_BOLD, 54), 180, y + 8, W - 240, T)
    cf = font(F_XB, 60); tw = cf.getlength(CTA)
    d.rounded_rectangle([W / 2 - tw / 2 - 40, 960, W / 2 + tw / 2 + 40, 960 + 120], radius=60, fill=ACC)
    d.text((W / 2, 1020), CTA, font=cf, anchor="mm", fill=BG)
    draw_rich(im, "Reference information, not a substitute for trained medical help.", font(F_SEMI, 28), W / 2, 1120, W * .8, T, anchor="m", color=DIM)

if __name__ == "__main__":
    cover("cover-reel-01-grid-down", ["THE GRID", "IS DOWN."], "No internet. No signal. *Still answers.*", last("phone", "water"), 1500)
    cover("cover-reel-02-medical", ["MEDICAL", "EMERGENCY.", "NO SIGNAL."], "What's on *one USB stick.*", last("phone", "tourniquet"), 1500)
    cover("cover-reel-03-every-phone", ["ONE USB.", "EVERY PHONE."], "The whole library, *offline.*", last("phone", "home", 0), 1500)
    thumb()
    for i, b in enumerate([s1, s2, s3, s4, s5], 1): slide(i, b)
