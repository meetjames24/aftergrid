#!/usr/bin/env python3
"""Aftergrid social kit compositor.
Turns recorded Field Mode footage (foot/<form>/<clip>/) into branded reels (1080x1920) and landscape
videos (1920x1080). One mp4 per scene, joined with the concat demuxer, then a synthesized sound bed.
Usage: python3 kit.py <video-name> [--frames t1,t2,...]   (--frames: write stills at scene-local times only)
"""
import json, math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
FOOT = f"{ROOT}/foot"
OUT = f"{ROOT}/out"
FPS = 30
BG, CARD, LINE, TXT, DIM, ACC, SLATE = "#14171a", "#1f2428", "#30373d", "#e9ecef", "#9aa4ad", "#f2a33a", "#3a444c"
F_HEAD = "/usr/share/fonts/truetype/google-fonts/ofl/archivoblack/ArchivoBlack-Regular.ttf"
F_BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
F_SEMI = "/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf"
F_XB = "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf"
CTA = "getaftergrid.com"
_fc = {}
def font(path, size):
    k = (path, int(size))
    if k not in _fc: _fc[k] = ImageFont.truetype(path, int(size))
    return _fc[k]
def ease(t): t = max(0., min(1., t)); return 1 - (1 - t) ** 3
def hexrgb(h, a=255): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)
def mix(c, a, under=BG):
    """Solid colour = c at alpha a (0-255) over `under`; for drawing straight onto frames."""
    c = c if isinstance(c, tuple) else hexrgb(c); u = hexrgb(under); a = max(0, min(255, a)) / 255
    return tuple(int(u[i] + (c[i] - u[i]) * a) for i in range(3)) + (255,)

# ---------------------------------------------------------------- footage
class Footage:
    """A recorded clip: frames with on-screen durations. speed applies after the typing ends."""
    def __init__(self, form, clip, query=None, speed=1.0, size=None, start=0.0, end_hold=None):
        self.dir = f"{FOOT}/{form}/{clip}"
        man = json.load(open(f"{self.dir}/manifest.json"))
        d = [x["d"] for x in man]
        # keystrokes: frames between the 0.35 s "focus" shot and the 0.45 s "done typing" shot
        self.keys, self.typed_end = [], None
        if query:
            i0 = next(i for i, x in enumerate(d) if abs(x - .35) < 1e-6)
            self.key_idx = list(range(i0 + 1, i0 + 1 + len(query)))
            self.typed_end = i0 + len(query) + 1
        last = len(d) - 1
        dd = [x if (self.typed_end is None or i <= self.typed_end or i == last) else x / speed for i, x in enumerate(d)]
        if end_hold: dd[last] = end_hold
        self.t = np.cumsum([0] + dd)          # start time of each frame
        self.files = [x["f"] for x in man]
        self.dur = float(self.t[-1]) - start
        self.start = start
        if query: self.keys = [float(self.t[i]) - start for i in self.key_idx]
        self.size, self._cache = size, {}
    def frame(self, t):
        i = int(np.searchsorted(self.t, t + self.start, side='right') - 1)
        i = max(0, min(i, len(self.files) - 1))
        if i not in self._cache:
            im = Image.open(f"{self.dir}/{self.files[i]}").convert("RGB")
            if self.size: im = im.resize(self.size, Image.LANCZOS)
            if len(self._cache) > 6: self._cache.pop(next(iter(self._cache)))
            self._cache[i] = im
        return self._cache[i]
    def typed(self, t, q):
        return q[:sum(1 for k in self.keys if k <= t)]

# ---------------------------------------------------------------- drawing helpers
def mark(d, x, y, s, gap=None):
    """Aftergrid mark: 3x3 rounded squares, top-right amber."""
    c = s / 3.3; g = gap or c * .15
    for r in range(3):
        for k in range(3):
            d.rounded_rectangle([x + k * (c + g), y + r * (c + g), x + k * (c + g) + c, y + r * (c + g) + c],
                                radius=c * .22, fill=ACC if (r == 0 and k == 2) else SLATE)
def tracked(d, xy, text, f, fill, track=0.0, anchor="l"):
    """Text with letter spacing (Archivo wordmark style). anchor l|m on x."""
    w = sum(f.getlength(ch) for ch in text) + track * f.size * (len(text) - 1)
    x, y = xy
    if anchor == "m": x -= w / 2
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill); x += f.getlength(ch) + track * f.size
    return w
def wordmark(d, x, y, h, anchor="l", color=TXT):
    f = font(F_HEAD, h)
    w = sum(f.getlength(ch) for ch in "AFTERGRID") + .14 * h * 8
    tot = h * 1.25 + h * .45 + w
    if anchor == "m": x -= tot / 2
    mark(d, x, y - h * .02, h * 1.25)
    tracked(d, (x + h * 1.7, y - h * .08), "AFTERGRID", f, color, .14)
    return tot

def rich_lines(text, f, maxw):
    """Wrap text; *word* marks amber words. Returns lines of [(word, amber)]."""
    words, amber, out = [], False, []
    for tok in text.split(" "):
        opens, closes = tok.startswith("*"), tok.rstrip(".,:;!?").endswith("*")
        a = amber or opens
        if opens: amber = True
        if closes: amber = False
        words.append((tok.replace("*", ""), a))
    line, lw, sp = [], 0, f.getlength(" ")
    for w, a in words:
        wl = f.getlength(w)
        if line and lw + sp + wl > maxw: out.append(line); line, lw = [], 0
        line.append((w, a)); lw += (sp if lw else 0) + wl
    if line: out.append(line)
    return out
def draw_rich(img, text, f, x, y, maxw, t, lh=1.12, anchor="l", stagger=0.045, color=TXT):
    """Words pop in one after another (slide up + fade)."""
    lines = rich_lines(text, f, maxw); n = 0
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    for li, line in enumerate(lines):
        lw = sum(f.getlength(w) for w, _ in line) + f.getlength(" ") * (len(line) - 1)
        cx = x - lw / 2 if anchor == "m" else x
        for w, a in line:
            p = ease((t - n * stagger) / .32); n += 1
            if p > 0:
                col = hexrgb(ACC if a else color, int(255 * p))
                d.text((cx, y + li * f.size * lh + (1 - p) * f.size * .35), w, font=f, fill=col)
            cx += f.getlength(w + " ")
    img.alpha_composite(layer)
    return y + len(lines) * f.size * lh

def pill(d, x, y, text, f, fg=BG, bg=ACC, pad=(18, 9)):
    w = f.getlength(text)
    d.rounded_rectangle([x, y, x + w + pad[0] * 2, y + f.size + pad[1] * 2], radius=(f.size + pad[1] * 2) / 2, fill=bg)
    d.text((x + pad[0], y + pad[1] - f.size * .1), text, font=f, fill=fg)
    return w + pad[0] * 2

def grid_bg(W, H, t=0, glow=0.0):
    """Dark background with a faint field grid and an amber glow."""
    im = Image.new("RGBA", (W, H), BG); d = ImageDraw.Draw(im)
    step = W // 9
    off = int((t * 18) % step)
    for x in range(-step, W + step, step): d.line([(x + off, 0), (x + off, H)], fill=mix((255, 255, 255), 9), width=1)
    for y in range(-step, H + step, step): d.line([(0, y + off), (W, y + off)], fill=mix((255, 255, 255), 9), width=1)
    if glow:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
        r = W * .55; gd.ellipse([W / 2 - r, H * .62 - r, W / 2 + r, H * .62 + r], fill=hexrgb(ACC, int(46 * glow)))
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(W // 6)))
    return im

# ---------------------------------------------------------------- scenes (each: dur, render(t)->RGBA, events)
class Scene:
    def __init__(self, dur, render, events=()):
        self.dur, self.render, self.events = dur, render, list(events)

def hook(W, H, lines, sub=None, sub_at=1.4, dur=3.4, flicker=True, amber_last=True):
    """Big type on black; lights flicker off like a power cut."""
    big = font(F_HEAD, W * (.135 if W < H else .085))
    sf = font(F_SEMI, W * (.05 if W < H else .028))
    rnd = random.Random(7); flick = [rnd.random() for _ in range(200)]
    def r(t):
        im = grid_bg(W, H, t); d = ImageDraw.Draw(im)
        y0 = H * (.34 if W < H else .27)
        for i, ln in enumerate(lines):
            p = ease((t - .12 - i * .32) / .25)
            if p <= 0: continue
            col = ACC if (amber_last and i == len(lines) - 1) else TXT
            on = 1.0
            if flicker and i == 0 and 0.55 < t < 1.1: on = .25 if flick[int(t * 30)] < .45 else 1
            f = big
            tw = f.getlength(ln)
            if tw > W * .88: f = font(F_HEAD, big.size * W * .88 / tw)
            d.text((W / 2, y0 + i * big.size * 1.08 + (1 - p) * 40), ln, font=f, anchor="ma", fill=mix(col, int(255 * p * on)))
        if sub:
            yy = y0 + len(lines) * big.size * 1.08 + H * .03
            draw_rich(im, sub, sf, W / 2, yy, W * .8, t - sub_at, anchor="m", color=DIM)
        # power-cut vignette pulse at the start
        if t < .35:
            ov = Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - t / .35)))); im.alpha_composite(ov)
        return im
    return Scene(dur, r, [("thump", 0.12), ("thump2", 0.62)])

def statement(W, H, text, dur=2.6, size=None, sub=None):
    f = font(F_HEAD, size or W * (.085 if W < H else .055))
    sf = font(F_SEMI, W * (.044 if W < H else .026))
    def r(t):
        im = grid_bg(W, H, t, glow=.6); y = draw_rich(im, text, f, W / 2, H * (.38 if W < H else .32), W * .84, t, lh=1.08, anchor="m", stagger=.07)
        if sub: draw_rich(im, sub, sf, W / 2, y + H * .03, W * .8, t - .7, anchor="m", color=DIM)
        return im
    return Scene(dur, r, [("whoosh", 0)])

def steps(W, H, items, dur=4.6):
    f = font(F_HEAD, W * (.07 if W < H else .046)); nf = font(F_HEAD, W * (.07 if W < H else .046))
    def r(t):
        im = grid_bg(W, H, t, glow=.35); d = ImageDraw.Draw(im)
        y0 = H * (.3 if W < H else .25); gap = f.size * 2.1
        for i, s in enumerate(items):
            p = ease((t - .15 - i * .9) / .35)
            if p <= 0: continue
            x = W * (.1 if W < H else .2)
            a = int(255 * p); yy = y0 + i * gap + (1 - p) * 30
            d.rounded_rectangle([x, yy - f.size * .12, x + f.size * 1.3, yy + f.size * 1.18], radius=f.size * .25, fill=mix(ACC, a))
            d.text((x + f.size * .65, yy + f.size * .52), str(i + 1), font=nf, anchor="mm", fill=mix(BG, 255, under=ACC) if a > 200 else mix(ACC, a))
            draw_rich(im, s, font(F_BOLD, f.size * .78), x + f.size * 1.75, yy + f.size * .08, W * .7, (t - .15 - i * .9) * 2, stagger=.02)
        return im
    return Scene(dur, r, [("whoosh", 0)] + [("tick", .15 + i * .9) for i in range(len(items))])

def outro(W, H, line1="When the grid goes down,", line2="Aftergrid boots up.", facts=None, dur=4.2, disclaimer=None):
    portrait = W < H
    def r(t):
        im = grid_bg(W, H, t, glow=1.0); d = ImageDraw.Draw(im)
        p = ease(t / .5)
        h = W * (.075 if portrait else .045)
        y = H * (.3 if portrait else .24)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        wordmark(ld, W / 2, y + (1 - p) * 30, h, anchor="m")
        lay.putalpha(Image.eval(lay.getchannel("A"), lambda a: int(a * p))); im.alpha_composite(lay)
        y2 = draw_rich(im, line1 + " *" + line2.replace(" ", "* *") + "*", font(F_BOLD, W * (.06 if portrait else .036)),
                       W / 2, y + h * 2.2, W * .86, t - .35, anchor="m", stagger=.06)
        if facts:
            draw_rich(im, facts, font(F_SEMI, W * (.036 if portrait else .021)), W / 2, y2 + H * .025, W * .8, t - 1.0, anchor="m", color=DIM, stagger=.02)
        q = ease((t - 1.5) / .4)
        if q > 0:
            cf = font(F_XB, W * (.055 if portrait else .032)); tw = cf.getlength(CTA)
            bx, by = W / 2 - tw / 2 - 34, H * (.66 if portrait else .7)
            d.rounded_rectangle([bx, by + (1 - q) * 20, bx + tw + 68, by + cf.size * 1.9 + (1 - q) * 20], radius=cf.size * .95, fill=mix(ACC, int(255 * q)))
            d.text((W / 2, by + cf.size * .95 + (1 - q) * 20), CTA, font=cf, anchor="mm", fill=hexrgb(BG) if q > .8 else mix(ACC, int(255 * q)))
        if disclaimer:
            draw_rich(im, disclaimer, font(F_SEMI, W * (.026 if portrait else .015)), W / 2, H * (.86 if portrait else .88), W * .84, t - 1.8, anchor="m", color=DIM, stagger=.01)
        return im
    return Scene(dur, r, [("whoosh", 0), ("rise", 0.2)])

# ---- footage scenes
def reel_band(im, W, label, t):
    d = ImageDraw.Draw(im)
    wordmark(d, 60, 168, 30)
    lf = font(F_BOLD, 34)
    if label: pill(d, W - 60 - lf.getlength(label) - 36, 160, label, lf, fg=ACC, bg=mix(ACC, 38))

def reel_search(clip, query, label, hold_extra=0.0, form="phone", after=None):
    W, H = 1080, 1920
    fo = Footage(form, clip, query)
    qf = font(F_HEAD, 92)
    def r(t):
        im = grid_bg(W, H, t); d = ImageDraw.Draw(im)
        reel_band(im, W, "OFFLINE", t)
        draw_rich(im, label, font(F_BOLD, 56), 60, 250, W - 120, t, stagger=.03, color=DIM)
        s = fo.typed(t, query)
        if after and t > fo.typed_end_t + after[0]:
            draw_rich(im, after[1], font(F_HEAD, 70), 60, 330, W - 120, t - fo.typed_end_t - after[0], lh=1.05)
        else:
            f = qf if qf.getlength(query) < W - 160 else font(F_HEAD, 92 * (W - 160) / qf.getlength(query))
            d.text((60, 335), s, font=f, fill=ACC)
            if int(t * 2.2) % 2 == 0 or len(s) < len(query):
                cx = 60 + f.getlength(s) + 8
                d.rectangle([cx, 345, cx + 10, 345 + f.size * 1.02], fill=ACC)
        fr = fo.frame(t).crop((0, 0, 1080, 1450))
        im.paste(fr, (0, 470)); d.line([(0, 469), (W, 469)], fill=ACC, width=3)
        return im
    fo.typed_end_t = float(fo.t[fo.typed_end]) if fo.typed_end is not None else 0
    ev = [("whoosh", 0)] + [("key", k) for k in fo.keys] + [("enter", fo.typed_end_t + .4)]
    return Scene(fo.dur + hold_extra, r, ev)

def reel_footage(clip, label, caption, form="phone", speed=1.0, query=None, badge=None, trim=None):
    W, H = 1080, 1920
    fo = Footage(form, clip, query, speed=speed, end_hold=3.5 if speed > 1 else None)
    def r(t):
        im = grid_bg(W, H, t); d = ImageDraw.Draw(im)
        reel_band(im, W, label, t)
        draw_rich(im, caption, font(F_HEAD, 64), 60, 250, W - 120, t, lh=1.07)
        fr = fo.frame(t).crop((0, 0, 1080, 1450))
        im.paste(fr, (0, 470)); d.line([(0, 469), (W, 469)], fill=ACC, width=3)
        if badge and query and fo.typed_end is not None and t > float(fo.t[fo.typed_end]):
            bf = font(F_XB, 34); pill(d, 60, 1780, badge, bf)
        return im
    ev = [("whoosh", 0)] + [("key", k) for k in fo.keys]
    return Scene(trim or fo.dur, r, ev)

# landscape: caption column left, framed screen right
def land_frame(im, fr, t, W=1920, H=1080):
    sw, sh = 1300, 731
    x, y = W - sw - 70, (H - sh) // 2 + 20
    sh_ = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh_)
    sd.rounded_rectangle([x - 4, y + 18, x + sw + 4, y + sh + 30], radius=22, fill=(0, 0, 0, 150))
    im.alpha_composite(sh_.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([x - 2, y - 38, x + sw + 2, y + sh + 2], radius=16, fill=CARD, outline=LINE)
    for i, c in enumerate(["#e5645a", "#f2a33a", "#5cc28a"]): d.ellipse([x + 18 + i * 26, y - 25, x + 32 + i * 26, y - 11], fill=c)
    d.rounded_rectangle([x + 110, y - 30, x + 520, y - 8], radius=11, fill=BG)
    d.text((x + 126, y - 29), "localhost  ·  offline", font=font(F_SEMI, 17), fill=DIM)
    m = Image.new("L", (sw, sh), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, sw, sh], radius=10, fill=255)
    im.paste(fr.resize((sw, sh), Image.LANCZOS), (x, y), m)
def land_band(im, label):
    d = ImageDraw.Draw(im); wordmark(d, 70, 58, 26)
    if label: pill(d, 70, 150, label, font(F_BOLD, 26), fg=ACC, bg=mix(ACC, 38))
def land_search(clip, query, label, form="desk", hold_extra=0.0):
    W, H = 1920, 1080
    fo = Footage(form, clip, query)
    def r(t):
        im = grid_bg(W, H, t); d = ImageDraw.Draw(im); land_band(im, "SEARCHED OFFLINE")
        draw_rich(im, label, font(F_BOLD, 40), 70, 300, 440, t, stagger=.03, color=DIM)
        s = fo.typed(t, query); f = font(F_HEAD, min(64, 64 * 420 / max(1, font(F_HEAD, 64).getlength(query))))
        d.text((70, 380), s, font=f, fill=ACC)
        if int(t * 2.2) % 2 == 0 or len(s) < len(query):
            cx = 70 + f.getlength(s) + 6; d.rectangle([cx, 388, cx + 7, 388 + f.size], fill=ACC)
        land_frame(im, fo.frame(t), t); return im
    te = float(fo.t[fo.typed_end])
    return Scene(fo.dur + hold_extra, r, [("whoosh", 0)] + [("key", k) for k in fo.keys] + [("enter", te + .4)])
def land_footage(clip, label, caption, form="desk", speed=1.0, query=None, badge=None):
    W, H = 1920, 1080
    fo = Footage(form, clip, query, speed=speed, end_hold=4.0 if speed > 1 else None)
    def r(t):
        im = grid_bg(W, H, t); d = ImageDraw.Draw(im); land_band(im, label)
        draw_rich(im, caption, font(F_HEAD, 52), 70, 300, 430, t, lh=1.08)
        if badge and query and t > float(fo.t[fo.typed_end]): pill(d, 70, 900, badge, font(F_XB, 26))
        land_frame(im, fo.frame(t), t); return im
    return Scene(fo.dur, r, [("whoosh", 0)] + [("key", k) for k in fo.keys])

# ---------------------------------------------------------------- videos
def V_reel_griddown():
    W, H = 1080, 1920
    return (W, H), [
        hook(W, H, ["THE GRID", "IS DOWN."], "No internet. No cell signal. *Now what?*", sub_at=1.3, dur=3.3),
        reel_search("water", "water filter", "Clean water?"),
        reel_search("fallout", "fallout shelter", "Fallout?"),
        reel_search("food", "food storage", "Food that lasts?"),
        reel_footage("map", "MAPS", "Street maps. *No signal needed.*"),
        reel_footage("askwater", "OFFLINE AI", "Or just ask. *It shows its sources.*", speed=3.2,
                     query="How do I make water safe to drink with bleach?", badge="▶▶  SPED UP · RUNS ON A LAPTOP CPU"),
        reel_footage("home", "ONE USB STICK", "Medical. Water. Food. Power. Comms. *One USB stick.*"),
        outro(W, H, facts="Boots from USB on most PCs. Works with no internet. Shares to phones over Wi-Fi."),
    ]
def V_reel_medical():
    W, H = 1080, 1920
    return (W, H), [
        hook(W, H, ["MEDICAL", "EMERGENCY.", "NO SIGNAL."], "Help could be *hours away.*", sub_at=1.5, dur=3.6),
        reel_search("tourniquet", "tourniquet", "Severe bleeding?"),
        reel_search("choking", "choking", "Choking?"),
        reel_search("anaphylaxis", "anaphylaxis", "Allergic reaction?"),
        reel_search("heatstroke", "heat stroke", "Heat stroke?"),
        reel_footage("askheat", "OFFLINE AI", "Ask in plain words. *Answers cite the library.*", speed=3.2,
                     query="What are the warning signs of heat stroke?", badge="▶▶  SPED UP · RUNS ON A LAPTOP CPU"),
        reel_footage("medtopic", "MEDICAL", "Medical encyclopedia + Army field manuals. *All offline.*"),
        outro(W, H, facts="A full medical encyclopedia, field manuals, maps and an offline AI on one USB stick.",
              disclaimer="Reference information, not a substitute for trained medical help. Call for help whenever you can."),
    ]
def V_reel_phones():
    W, H = 1080, 1920
    return (W, H), [
        hook(W, H, ["NO INTERNET?", "STILL ANSWERS."], dur=2.6),
        steps(W, H, ["Plug the USB into a PC", "Boot *Aftergrid*", "Everything works *offline*"], dur=3.6),
        reel_footage("home", "ON ANY PHONE", "Phones join its Wi-Fi. *The whole library, on every phone.*"),
        reel_footage("langs", "6 LANGUAGES", "English · Ελληνικά · Français · Deutsch · Português · *Türkçe*"),
        outro(W, H, facts="Medical. Water. Food. Power. Comms. Maps. Offline AI."),
    ]
def V_land_demo():
    W, H = 1920, 1080
    return (W, H), [
        hook(W, H, ["THE GRID IS DOWN.", "NOW WHAT?"], "No internet. No cell signal. *Aftergrid still answers.*", sub_at=1.3, dur=3.6),
        land_search("water", "water filter", "Clean water?"),
        land_search("tourniquet", "tourniquet", "Severe bleeding?"),
        land_search("choking", "choking", "Choking?"),
        land_footage("map", "OFFLINE MAPS", "Every road. *No signal needed.*"),
        land_footage("askwater", "OFFLINE AI", "Ask like a person. *It cites its sources.*", speed=3.2,
                     query="How do I make water safe to drink with bleach?", badge="▶▶  SPED UP · LAPTOP CPU"),
        land_footage("medtopic", "MEDICAL", "Medical encyclopedia. *Army field manuals.*"),
        land_footage("langs", "6 LANGUAGES", "Speaks *your* language."),
        steps(W, H, ["Plug the USB into a PC", "Boot *Aftergrid*. Logins saved, encrypted",
                     "Library, maps and AI work *offline*", "Share it to nearby phones over *Wi-Fi*"], dur=5.0),
        outro(W, H, facts="Boots from USB on most Windows PCs and Intel Macs. No internet needed.",
              disclaimer="Reference information, not a substitute for trained help.", dur=4.6),
    ]
VIDEOS = {"reel-01-grid-down": V_reel_griddown, "reel-02-medical-emergency": V_reel_medical,
          "reel-03-every-phone": V_reel_phones, "landscape-01-aftergrid-demo": V_land_demo}

# ---------------------------------------------------------------- sound
SR = 48000
def tone(f, dur, amp=1.0):
    t = np.arange(int(dur * SR)) / SR; return amp * np.sin(2 * np.pi * f * t)
def env_exp(n, k): return np.exp(-np.arange(n) / (SR * k))
def lowpass(x, a):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)): acc += a * (x[i] - acc); y[i] = acc
    return y
_rng = np.random.default_rng(3)
def sfx(kind):
    if kind == "key":
        n = int(.03 * SR); z = _rng.standard_normal(n); z = np.diff(z, prepend=0) * env_exp(n, .004)
        return .16 * (z + .5 * tone(_rng.uniform(1700, 2400), .03) * env_exp(n, .003))
    if kind == "enter":
        n = int(.06 * SR); z = np.diff(_rng.standard_normal(n), prepend=0) * env_exp(n, .008)
        return .24 * (z + tone(900, .06) * env_exp(n, .01))
    if kind in ("thump", "thump2"):
        n = int(.7 * SR); t = np.arange(n) / SR; f = 70 * np.exp(-t * 3) + 32
        return (.9 if kind == "thump" else .6) * np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, .18)
    if kind == "whoosh":
        n = int(.45 * SR); z = _rng.standard_normal(n); e = np.sin(np.linspace(0, np.pi, n)) ** 2
        return .10 * lowpass(z, .08) * e * 4
    if kind == "tick":
        n = int(.12 * SR); return .25 * tone(1320, .12) * env_exp(n, .025)
    if kind == "rise":
        n = int(1.6 * SR); t = np.arange(n) / SR
        return .12 * (np.sin(2 * np.pi * 220 * t) + .5 * np.sin(2 * np.pi * 330 * t) + .3 * np.sin(2 * np.pi * 440 * t)) * np.minimum(1, t / .5) * np.exp(-np.maximum(0, t - .6) * 2.2)
    return np.zeros(1)
def bed(dur, hook_end):
    """Dark ambient bed: A-minor drone, slow swell, soft pulse from the end of the hook."""
    n = int(dur * SR); t = np.arange(n) / SR
    lfo = .6 + .4 * np.sin(2 * np.pi * t / 7)
    x = sum(a * np.sin(2 * np.pi * f * t + ph) for f, a, ph in [(55, .30, 0), (82.4, .16, 1), (110, .14, 2), (164.8, .06, .5), (220, .04, 1.3)]) * lfo
    x += .05 * lowpass(_rng.standard_normal(n), .01) * 6
    beat = 60 / 92; pulse = np.zeros(n)
    k = int(.25 * SR); kick = np.sin(2 * np.pi * np.cumsum(55 * np.exp(-np.arange(k) / SR * 12) + 40) / SR) * env_exp(k, .07)
    s = hook_end
    while s < dur - .4:
        i = int(s * SR); pulse[i:i + k] += kick[:max(0, min(k, n - i))]; s += beat
    x = x * np.minimum(1, t / 1.0) * np.minimum(1, (dur - t) / 1.2) + .35 * pulse * np.minimum(1, (dur - t) / 1.2)
    return x
def make_audio(path, dur, events, hook_end):
    x = bed(dur, hook_end) * .55
    for kind, at in events:
        s = sfx(kind); i = int(at * SR)
        if 0 <= i < len(x): x[i:i + len(s)] += s[:len(x) - i]
    x = np.tanh(x * 1.1); x = x / max(1e-6, np.abs(x).max()) * .85
    st = np.stack([x, x], 1); st = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())

# ---------------------------------------------------------------- render
ENC = ["-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS)]
def render_scene(sc, size, path):
    W, H = size; n = int(round(sc.dur * FPS)); tmp = path[:-4] + ".part.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"] + ENC + [tmp], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / FPS; im = sc.render(t).convert("RGB")
        # quick fade in from black over the first 4 frames for clean cuts
        if i < 4: im = Image.blend(Image.new("RGB", (W, H), BG), im, (i + 1) / 5)
        p.stdin.write(im.tobytes())
    p.stdin.close()
    if p.wait() != 0: raise SystemExit("ffmpeg failed " + path)
    os.replace(tmp, path)

def main():
    name = sys.argv[1]; size, scenes = VIDEOS[name]()
    if "--frames" in sys.argv:   # stills for checking: "--frames 2:1.5,5:3" = scene:time
        os.makedirs(f"{OUT}/check", exist_ok=True)
        for spec in sys.argv[sys.argv.index("--frames") + 1].split(","):
            si, t = spec.split(":"); scenes[int(si)].render(float(t)).convert("RGB").save(f"{OUT}/check/{name}-s{si}-{t}.jpg", quality=88)
        return
    wd = f"{OUT}/work/{name}"; os.makedirs(wd, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    files, events, t0 = [], [], 0.0
    for i, sc in enumerate(scenes):
        f = f"{wd}/s{i:02d}.mp4"; render_scene(sc, size, f); files.append(f)
        events += [(k, t0 + a) for k, a in sc.events]; t0 += round(sc.dur * FPS) / FPS
        print(f"  scene {i} {sc.dur:.1f}s", flush=True)
    open(f"{wd}/list.txt", "w").write("".join(f"file '{f}'\n" for f in files))
    make_audio(f"{wd}/audio.wav", t0, events, scenes[0].dur)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{wd}/list.txt", "-c", "copy", f"{wd}/video.mp4"], check=True)
    tmp = f"{OUT}/{name}.part.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{wd}/video.mp4", "-i", f"{wd}/audio.wav", "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, f"{OUT}/{name}.mp4"); print(name, f"{t0:.1f}s")


def V_check():
    W, H = 1080, 1920
    return (W, H), [hook(W, H, ["THE GRID", "IS DOWN."], "No internet. No cell signal. *Now what?*", sub_at=1.3, dur=3.3),
                    reel_search("water", "water filter", "Clean water?"), reel_footage("map", "MAPS", "Street maps. *No signal needed.*"),
                    steps(W, H, ["Plug the USB into a PC", "Boot *Aftergrid*", "Everything works *offline*"], dur=3.6),
                    outro(W, H, facts="Boots from USB on most PCs. Works with no internet.", disclaimer="Reference information, not a substitute for trained medical help.")]
VIDEOS["check"] = V_check
if __name__ == "__main__": main()
