#!/usr/bin/env python3
"""Aftergrid first-aid diagrams: pictogram-style SVGs drawn from code (one function per card).
Output: content/cards/diagrams/<card-id>.svg (+ .png previews with --png).
Style: thick round strokes; casualty = slate, helper = amber, blood/danger = red, cooling = blue, check = green.
"""
import math, os, subprocess, sys

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagrams")
W, H = 900, 560
SLATE, AMBER, RED, BLUE, GREEN, INK, DIM, PAPER, LINE = "#3A444C", "#E0861A", "#C2402C", "#2F7FC1", "#2F8A57", "#1F1E1C", "#6E6A60", "#FFFFFF", "#E6E2D7"
FONT = "Inter, 'Noto Sans', 'DejaVu Sans', sans-serif"

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def svg(body, w=W, h=H):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="{FONT}">'
            f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="18" fill="{PAPER}" stroke="{LINE}" stroke-width="2"/>{body}</svg>')
def seg(*pts, c=SLATE, w=22, fill="none"):
    d = "M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    return f'<path d="{d}" fill="{fill}" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
def curve(d, c=SLATE, w=22, fill="none"):
    return f'<path d="{d}" fill="{fill}" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
def dot(x, y, r, c=SLATE): return f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{c}"/>'
def txt(x, y, s, size=26, c=INK, w=700, anchor="start"):
    lines = s.split("\n")
    return "".join(f'<text x="{x}" y="{y + i * size * 1.22:.0f}" font-size="{size}" font-weight="{w}" fill="{c}" text-anchor="{anchor}">{esc(l)}</text>' for i, l in enumerate(lines))
def arrow(x1, y1, x2, y2, c=RED, w=8, head=22):
    a = math.atan2(y2 - y1, x2 - x1); hx, hy = x2 - head * math.cos(a), y2 - head * math.sin(a)
    p1 = (hx + head * .6 * math.sin(a), hy - head * .6 * math.cos(a)); p2 = (hx - head * .6 * math.sin(a), hy + head * .6 * math.cos(a))
    return (f'<line x1="{x1}" y1="{y1}" x2="{hx:.0f}" y2="{hy:.0f}" stroke="{c}" stroke-width="{w}" stroke-linecap="round"/>'
            f'<path d="M{x2},{y2} L{p1[0]:.0f},{p1[1]:.0f} L{p2[0]:.0f},{p2[1]:.0f} Z" fill="{c}"/>')
def badge(x, y, n, c=AMBER):
    return f'<circle cx="{x}" cy="{y}" r="22" fill="{c}"/>' + txt(x, y + 9, str(n), 26, "#FFFFFF", 800, "middle")
def cross(x, y, r=26): return seg((x - r, y - r), (x + r, y + r), c=RED, w=9) + seg((x - r, y + r), (x + r, y - r), c=RED, w=9)
def tick(x, y, r=22): return seg((x - r, y), (x - r * .3, y + r * .7), (x + r, y - r * .8), c=GREEN, w=9)
def ground(y=480, x1=40, x2=W - 40): return f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{LINE}" stroke-width="4"/>'
def divider(x): return f'<line x1="{x}" y1="40" x2="{x}" y2="{H-40}" stroke="{LINE}" stroke-width="3" stroke-dasharray="6 10"/>'

# ---------------------------------------------------------------- people
def lying(x, y, s=1.0, c=SLATE, head_left=True):
    """Casualty on their back, side view. (x, y) = point on the chest where hands go."""
    k = 1 if head_left else -1
    return (dot(x - k * 150 * s, y + 18 * s, 30 * s, c) +                    # head
            seg((x - k * 110 * s, y + 24 * s), (x + k * 110 * s, y + 24 * s), c=c, w=52 * s) +   # torso
            seg((x + k * 120 * s, y + 30 * s), (x + k * 300 * s, y + 34 * s), c=c, w=30 * s) +   # legs
            seg((x - k * 60 * s, y + 30 * s), (x + k * 70 * s, y + 40 * s), c=c, w=16 * s))      # arm along body

def cpr():
    hx, hy = 270, 392                      # hands on the centre of the chest
    b = ground(470, 40, 540)
    # helper kneeling on the far side: shin on the ground, thigh up, torso leaning in, arms locked straight
    b += seg((120, 466), (232, 466), (216, 350), c=AMBER, w=26)          # shin + thigh
    b += seg((216, 350), (hx, 236), c=AMBER, w=34)                         # torso
    b += dot(hx + 28, 186, 32, AMBER)                                      # head
    b += seg((hx, 240), (hx, hy - 4), c=AMBER, w=20)                      # straight arms
    b += lying(hx, hy + 10, .86)
    b += f'<rect x="{hx-26}" y="{hy-14}" width="52" height="20" rx="8" fill="{AMBER}"/>'   # heel of hands
    b += arrow(hx + 64, 300, hx + 64, 384, RED, 9)
    b += txt(hx, 520, "Push 5–6 cm (2 in) deep", 26, INK, 800, "middle")
    b += txt(600, 92, "Centre of the chest", 30) + txt(600, 130, "Arms straight, shoulders\nover your hands", 24, DIM, 600)
    b += txt(600, 236, "100–120", 54, RED, 800) + txt(600, 272, "pushes a minute", 26)
    b += txt(600, 334, "Let the chest come\nall the way back up", 24, DIM, 600)
    b += txt(600, 430, "30 pushes : 2 breaths", 26) + txt(600, 462, "(or pushes only)", 22, DIM, 600)
    return svg(b)

def recovery():
    """Recovery position, seen from above: on their side, top hand under the cheek, top knee bent."""
    b = txt(50, 72, "Recovery position", 34, INK, 800)
    cx, cy = 430, 270
    b += dot(cx - 214, cy, 36)                                                       # head, tilted back
    b += seg((cx - 170, cy + 4), (cx + 40, cy + 8), w=60)                            # torso on its side
    b += seg((cx - 150, cy - 18), (cx - 110, cy - 110), (cx - 30, cy - 130), w=18)   # lower arm out at a right angle
    b += seg((cx - 140, cy + 28), (cx - 196, cy + 86), (cx - 246, cy + 40), w=18)    # top arm: hand under the cheek
    b += seg((cx + 40, cy + 8), (cx + 280, cy + 8), w=30)                            # bottom leg straight
    b += seg((cx + 40, cy + 20), (cx + 150, cy + 130), (cx + 270, cy + 120), w=30)   # top leg bent at hip and knee
    b += txt(60, 440, "Head tilted back:\nairway open", 24) + arrow(130, 400, 196, 300, AMBER, 6, 18)
    b += txt(290, 440, "Hand under cheek", 24) + arrow(300, 410, 220, 352, AMBER, 6, 18)
    b += txt(520, 470, "Top knee bent:\nstops them rolling", 24) + arrow(590, 436, 584, 412, AMBER, 6, 18)
    b += txt(620, 92, "Use when someone is\nbreathing but not awake.", 22, DIM, 600) + txt(620, 160, "Check breathing\nevery minute.", 22, DIM, 600)
    return svg(b)

def water():
    b = txt(50, 72, "Making water safe", 36, INK, 800)
    # panel 1: boil
    b += badge(80, 140, 1) + txt(118, 150, "Boil", 32, INK, 800)
    b += f'<rect x="60" y="220" width="170" height="100" rx="14" fill="none" stroke="{SLATE}" stroke-width="12"/>' + seg((40, 226), (250, 226), w=12)
    for x in (100, 145, 190): b += curve(f"M{x},206 q-10,-14 0,-26 q10,-12 0,-24", c=DIM, w=6)
    b += txt(60, 366, "Rolling boil", 26) + txt(60, 408, "1 minute", 40, RED, 800) + txt(60, 446, "3 min above 2,000 m\n(6,500 ft)", 22, DIM, 600)
    b += divider(300)
    # panel 2: bleach table
    b += badge(340, 140, 2) + txt(378, 150, "Plain bleach", 32, INK, 800) + txt(380, 184, "unscented, 6% or 8.25%", 22, DIM, 600)
    rows = [("", "1 litre", "4 litres"), ("Clear water", "2 drops", "8 drops"), ("Cloudy or cold", "4 drops", "16 drops")]
    y = 236
    for i, (a, c1, c2) in enumerate(rows):
        f = (22, DIM, 700) if i == 0 else (24, INK, 700)
        b += txt(340, y, a, *f) + txt(560, y, c1, *f) + txt(680, y, c2, *f)
        if i: b += f'<line x1="340" y1="{y+16}" x2="790" y2="{y+16}" stroke="{LINE}" stroke-width="2"/>'
        y += 50
    b += txt(340, 412, "Stir, cover, wait", 26) + txt(560, 412, "30 min", 40, RED, 800)
    b += txt(340, 456, "It should smell slightly of chlorine.\nFilter cloudy water through a cloth first.", 20, DIM, 600)
    b += txt(340, 524, "1 US gallon: 8 drops of 6%, or 6 drops of 8.25%", 18, DIM, 600)
    return svg(b)

def ors():
    b = txt(50, 72, "Oral rehydration solution", 36, INK, 800)
    # 1 litre bottle
    b += curve("M110,160 h60 v40 q30,20 30,60 v190 q0,20 -20,20 h-80 q-20,0 -20,-20 v-190 q0,-40 30,-60 z", c=SLATE, w=10)
    b += f'<rect x="96" y="300" width="88" height="160" rx="10" fill="{BLUE}" opacity=".25"/>'
    b += txt(140, 520, "1 litre", 30, INK, 800, "middle") + txt(140, 552, "clean water", 20, DIM, 600, "middle")
    b += txt(250, 330, "+", 60, DIM, 800, "middle")
    # 6 spoons of sugar
    for i in range(6):
        x, y = 320 + (i % 3) * 95, 230 + (i // 3) * 120
        b += f'<ellipse cx="{x}" cy="{y}" rx="34" ry="22" fill="{PAPER}" stroke="{SLATE}" stroke-width="8"/>' + seg((x + 30, y + 6), (x + 72, y + 30), w=10)
        b += f'<ellipse cx="{x}" cy="{y-4}" rx="24" ry="12" fill="#EFE7D5"/>'
    b += txt(415, 500, "6 level teaspoons", 28, INK, 800, "middle") + txt(415, 534, "sugar", 22, DIM, 600, "middle")
    b += txt(640, 330, "+", 60, DIM, 800, "middle")
    x, y = 760, 290
    b += f'<ellipse cx="{x}" cy="{y}" rx="34" ry="22" fill="{PAPER}" stroke="{SLATE}" stroke-width="8"/>' + seg((x + 30, y + 6), (x + 72, y + 30), w=10)
    b += f'<path d="M{x-24},{y-4} a24,12 0 0 0 24,12 v-24 a24,12 0 0 0 -24,12 z" fill="#E6E2D7"/>'
    b += txt(770, 500, "½ level teaspoon", 28, INK, 800, "middle") + txt(770, 534, "salt", 22, DIM, 600, "middle")
    b += txt(860, 120, "Small sips, often.", 22, DIM, 600, "end") + txt(860, 150, "After every loose stool.", 22, DIM, 600, "end")
    return svg(b)

def fast():
    b = txt(50, 72, "Stroke: think FAST", 36, INK, 800)
    tiles = [("F", "Face", "drooping on\none side?"), ("A", "Arms", "one drifts\ndown?"), ("S", "Speech", "slurred or\nstrange?"), ("T", "Time", "get help now.\nNote the time.")]
    for i, (L, name, q) in enumerate(tiles):
        x = 50 + i * 205
        b += f'<rect x="{x}" y="110" width="185" height="400" rx="18" fill="#FBF3E4" stroke="#EFD9B0" stroke-width="3"/>'
        b += txt(x + 92, 190, L, 76, RED if L == "T" else AMBER, 900, "middle")
        cx, cy = x + 92, 290
        if L == "F":
            b += f'<circle cx="{cx}" cy="{cy}" r="52" fill="none" stroke="{SLATE}" stroke-width="9"/>' + dot(cx - 20, cy - 12, 7) + dot(cx + 20, cy - 8, 7)
            b += curve(f"M{cx-26},{cy+18} q14,10 26,6 q14,0 26,22", c=SLATE, w=8)
        if L == "A":
            b += dot(cx, cy - 46, 20) + seg((cx, cy - 22), (cx, cy + 40), w=16) + seg((cx, cy - 10), (cx - 58, cy - 12), w=12) + seg((cx, cy - 10), (cx + 52, cy + 20), w=12)
            b += arrow(cx + 62, cy - 4, cx + 62, cy + 34, RED, 5, 14)
        if L == "S":
            b += curve(f"M{cx-56},{cy-36} h112 q14,0 14,14 v44 q0,14 -14,14 h-66 l-26,22 v-22 h-20 q-14,0 -14,-14 v-44 q0,-14 14,-14 z", c=SLATE, w=8)
            b += txt(cx, cy + 6, "~?~", 28, SLATE, 800, "middle")
        if L == "T":
            b += f'<circle cx="{cx}" cy="{cy}" r="52" fill="none" stroke="{SLATE}" stroke-width="9"/>' + seg((cx, cy), (cx, cy - 32), w=8) + seg((cx, cy), (cx + 24, cy + 10), w=8)
        b += txt(cx, 392, name, 30, INK, 800, "middle") + txt(cx, 432, q, 22, DIM, 600, "middle")
    return svg(b)


def standing_side(fx, c=SLATE, lean=0, ground_y=480, head=34):
    """Person standing, side view, facing right. Returns svg and joint points."""
    hip = (fx, 360); sh = (fx + lean, 250); hd = (fx + lean * 1.25 + 8, 250 - head - 18)
    b = seg((fx - 14, ground_y), hip, (fx + 18, ground_y), c=c, w=24) + seg(hip, sh, c=c, w=36) + dot(*hd, head, c)
    return b, hip, sh, hd

def choking():
    b = txt(50, 66, "Choking (adult or child over 1)", 32, INK, 800) + ground(480, 40, W - 40) + divider(450)
    # A: back blows. casualty leans forward, helper behind strikes between the shoulder blades
    cb, chip, csh, chd = standing_side(300, SLATE, lean=70)
    hb, hhip, hsh, hhd = standing_side(170, AMBER, lean=24)
    b += hb + seg(hsh, (250, 300), (330, 296), c=AMBER, w=18)             # striking arm
    b += cb + seg(csh, (csh[0] + 20, csh[1] + 70), c=SLATE, w=16)         # casualty arm hanging
    b += seg((hsh[0] + 6, hsh[1] + 26), (300, 330), (390, 300), c=AMBER, w=14)   # supporting arm across the chest
    b += arrow(300, 230, 338, 282, RED, 8)
    b += badge(70, 120, 1) + txt(106, 130, "5 back blows", 28) + txt(225, 510, "Heel of the hand,\nbetween the shoulder blades", 20, DIM, 700, "middle")
    # B: abdominal thrusts. helper behind, fist just above the navel, pull in and up
    cb, chip, csh, chd = standing_side(700, SLATE, lean=6)
    hb, hhip, hsh, hhd = standing_side(615, AMBER, lean=10)
    b += hb + cb + seg(csh, (csh[0] + 18, csh[1] + 90), c=SLATE, w=16)
    b += seg((hsh[0] + 4, hsh[1] + 16), (680, 330), (728, 322), c=AMBER, w=18) + dot(736, 320, 15, AMBER)   # arm around, fist
    b += arrow(800, 360, 760, 318, RED, 8)
    b += badge(480, 120, 2) + txt(516, 130, "5 abdominal thrusts", 28) + txt(675, 510, "Fist just above the navel,\npull sharply in and up", 20, DIM, 700, "middle")
    b += txt(860, 66, "Alternate 5 and 5", 22, RED, 800, "end")
    return svg(b)

def choking_infant():
    b = txt(50, 66, "Choking (baby under 1)", 32, INK, 800) + divider(450)
    # A: face down along the forearm, head lower, back blows
    b += seg((90, 270), (330, 350), c=AMBER, w=34)                                   # forearm, sloping down to the hand
    b += seg((330, 350), (352, 352), c=AMBER, w=26)                                  # hand supporting the jaw
    b += seg((170, 272), (300, 312), c=SLATE, w=34) + dot(336, 322, 22, SLATE)       # baby body + head (lower)
    b += seg((180, 280), (150, 318), c=SLATE, w=14) + seg((200, 286), (190, 330), c=SLATE, w=14)   # legs either side
    b += arrow(250, 200, 250, 270, RED, 8) + f'<rect x="216" y="176" width="70" height="22" rx="8" fill="{AMBER}"/>'
    b += badge(80, 120, 1) + txt(116, 130, "5 back blows", 28) + txt(80, 420, "Face down along your arm,\nhead lower than the body.\nSupport the jaw, not the throat.", 22, DIM, 600)
    # B: face up, head lower, two fingers on the centre of the chest
    b += seg((520, 270), (760, 350), c=AMBER, w=34) + seg((760, 350), (782, 352), c=AMBER, w=26)
    b += seg((600, 258), (730, 298), c=SLATE, w=34) + dot(766, 310, 22, SLATE)
    b += seg((664, 256), (676, 214), c=AMBER, w=12) + seg((680, 262), (692, 220), c=AMBER, w=12)   # two fingers
    b += arrow(720, 170, 690, 226, RED, 8)
    b += badge(490, 120, 2) + txt(526, 130, "5 chest thrusts", 28) + txt(490, 420, "Face up, head lower.\nTwo fingers, centre of the chest,\n4 cm (1.5 in) deep.", 22, DIM, 600)
    b += txt(450, 530, "Alternate 5 and 5. No abdominal thrusts on a baby.", 22, INK, 700, "middle")
    return svg(b)

def limb_leg(y=300):
    """A leg seen from the side: thigh on the left (towards the heart), knee, shin, foot."""
    return (seg((90, y), (470, y + 6), c=SLATE, w=96) + seg((470, y + 6), (780, y + 30), c=SLATE, w=74) +
            seg((780, y + 30), (820, y - 10), c=SLATE, w=56) + dot(470, y + 6, 52, SLATE))

def tourniquet():
    b = txt(50, 66, "Tourniquet: where it goes", 32, INK, 800)
    b += limb_leg(270)
    b += f'<ellipse cx="660" cy="292" rx="26" ry="30" fill="{RED}"/>' + curve("M650,320 q-6,40 4,70", c=RED, w=8)   # wound, bleeding
    b += f'<rect x="560" y="226" width="36" height="128" rx="10" fill="{AMBER}"/>'                                      # tourniquet above the wound
    b += f'<rect x="452" y="210" width="36" height="140" rx="10" fill="none" stroke="{AMBER}" stroke-width="6" stroke-dasharray="8 8"/>' + cross(470, 160, 22)
    b += txt(470, 124, "Not on a joint", 22, RED, 800, "middle")
    b += seg((578, 380), (578, 402), (660, 402), (660, 380), c=INK, w=4) + txt(619, 436, "5–7 cm (2–3 in)\nabove the wound", 22, INK, 800, "middle")
    b += txt(90, 400, "Towards the heart ←", 22, DIM, 700)
    b += txt(50, 486, "Tighten until the bleeding stops. It will hurt.", 24, INK, 800)
    b += txt(50, 522, "Write the time on it. Don't loosen it. Get to a hospital.", 22, DIM, 700)
    b += f'<circle cx="820" cy="120" r="40" fill="none" stroke="{SLATE}" stroke-width="8"/>' + seg((820, 120), (820, 94), w=7) + seg((820, 120), (840, 132), w=7)
    b += txt(820, 196, "note the\ntime", 20, DIM, 700, "middle")
    return svg(b)

def windlass():
    b = txt(50, 66, "No tourniquet? Make one", 32, INK, 800)
    steps = ["Wrap a strip of strong,\nnon-stretchy cloth,\n4 cm (1.5 in) or wider", "Tie a knot over a\nstick, pen or spoon", "Twist the stick until\nthe bleeding stops", "Tie the stick down\nso it can't unwind"]
    for i, cap in enumerate(steps):
        x = 60 + i * 205; cx, cy = x + 90, 250
        b += badge(x + 10, 120, i + 1)
        b += f'<circle cx="{cx}" cy="{cy}" r="62" fill="{SLATE}"/>'                                  # limb, cross-section
        tight = 6 if i < 2 else 0
        b += f'<circle cx="{cx}" cy="{cy}" r="{70 - tight * 0 - (4 if i >= 2 else 0)}" fill="none" stroke="{AMBER}" stroke-width="16"/>'
        if i >= 1: b += dot(cx, cy - 76, 12, AMBER)                                                   # knot on top
        if i == 1: b += seg((cx - 60, cy - 86), (cx + 60, cy - 86), c="#8A6A2C", w=12)               # stick over the knot
        if i == 2:
            b += seg((cx - 44, cy - 128), (cx + 44, cy - 44), c="#8A6A2C", w=12)
            b += curve(f"M{cx+70},{cy-120} a36,36 0 1 1 -12,-30", c=RED, w=6) + f'<path d="M{cx+52},{cy-158} l14,6 l-10,12 z" fill="{RED}"/>'
        if i == 3:
            b += seg((cx - 44, cy - 128), (cx + 44, cy - 44), c="#8A6A2C", w=12)
            b += seg((cx + 44, cy - 44), (cx + 70, cy - 2), c=AMBER, w=8)                            # tied down
        b += txt(cx, 380, cap, 20, INK, 700, "middle")
    b += txt(450, 520, "Never use wire, cord, string or anything elastic.", 22, RED, 800, "middle")
    return svg(b)

def pressure():
    b = txt(50, 66, "Stop the bleeding: press, pack", 32, INK, 800) + divider(450)
    # A: hands pressing a cloth on the wound
    b += seg((60, 360), (400, 360), c=SLATE, w=90)
    b += f'<rect x="170" y="296" width="120" height="30" rx="8" fill="#F5F1E8" stroke="{DIM}" stroke-width="4"/>'
    b += seg((230, 296), (230, 200), c=AMBER, w=30) + f'<rect x="186" y="270" width="88" height="34" rx="12" fill="{AMBER}"/>'
    b += seg((260, 296), (290, 190), c=AMBER, w=26) + f'<rect x="214" y="250" width="80" height="26" rx="10" fill="{AMBER}"/>'
    b += arrow(330, 190, 330, 286, RED, 8)
    b += badge(80, 120, 1) + txt(116, 130, "Press hard", 28) + txt(60, 450, "Cloth or gauze on the wound,\nboth hands, body weight.\nDon't lift to look.", 22, DIM, 600)
    # B: packing a deep wound
    b += seg((490, 360), (830, 360), c=SLATE, w=90)
    b += curve("M640,316 q20,-4 40,0 l-6,40 q-14,6 -28,0 z", c=RED, w=4, fill=RED)                 # deep wound
    b += curve("M660,330 q-30,-60 -60,-110 q-20,-30 -60,-30", c="#F5F1E8", w=18)                   # gauze going in
    b += curve("M660,330 q-30,-60 -60,-110 q-20,-30 -60,-30", c=DIM, w=2)
    b += seg((690, 210), (668, 320), c=AMBER, w=18) + seg((716, 214), (690, 318), c=AMBER, w=18)   # two fingers pushing it in
    b += badge(490, 120, 2) + txt(526, 130, "Pack deep wounds", 28) + txt(490, 450, "Push gauze or cloth into the wound\n(arm, leg, armpit, groin, neck),\nthen press hard on top.", 22, DIM, 600)
    return svg(b)

def splint():
    b = txt(50, 66, "Splint and sling", 32, INK, 800) + divider(450)
    # A: forearm on a board, tied above and below the break
    b += f'<rect x="70" y="270" width="340" height="40" rx="8" fill="#C9A66B"/>'                      # board
    b += seg((90, 250), (360, 250), c=SLATE, w=44) + seg((360, 250), (400, 240), c=SLATE, w=36)    # forearm + hand
    b += curve("M230,226 l10,22 l-12,10 l10,22", c=RED, w=6)                                       # break
    for x in (130, 330): b += f'<rect x="{x-12}" y="216" width="24" height="104" rx="6" fill="{AMBER}"/>'
    b += badge(80, 120, 1) + txt(116, 130, "Splint", 28) + txt(60, 380, "Pad it. Tie it above and below\nthe break so the joints either\nside can't move. Keep it as found.", 22, DIM, 600)
    # B: front view, arm in a triangular sling
    cx = 680
    b += dot(cx, 150, 32) + f'<rect x="{cx-48}" y="190" width="96" height="150" rx="24" fill="{SLATE}"/>'
    b += seg((cx - 34, 340), (cx - 40, 470), w=26) + seg((cx + 34, 340), (cx + 40, 470), w=26) + seg((cx - 50, 206), (cx - 90, 330), w=22)
    b += f'<path d="M{cx+50},200 L{cx-30},300 L{cx+90},300 Z" fill="{AMBER}" opacity=".9"/>'         # sling
    b += seg((cx + 48, 206), (cx + 76, 286), (cx - 6, 288), w=22)                                     # bent arm inside the sling
    b += badge(490, 120, 2) + txt(526, 130, "Sling", 28) + txt(490, 520, "Check fingers stay warm and pink.", 22, DIM, 600)
    return svg(b)

def nosebleed():
    b = txt(50, 66, "Nosebleed", 32, INK, 800) + divider(450)
    # A: leaning forward, pinching the soft part of the nose
    b += f'<circle cx="230" cy="250" r="78" fill="{SLATE}"/>' + f'<path d="M296,262 l34,22 l-30,12 z" fill="{SLATE}"/>'   # head + nose, tipped forward
    b += seg((190, 326), (160, 470), w=60)                                                          # body leaning forward
    b += seg((180, 360), (290, 330), (318, 290), c=AMBER, w=20) + dot(322, 284, 12, AMBER)         # arm, fingers pinching
    b += curve("M326,300 q4,20 -2,40", c=RED, w=6)
    b += tick(380, 140) + txt(230, 520, "Lean forward, pinch the soft part,\n10–15 minutes without letting go", 22, INK, 800, "middle")
    # B: head tipped back: no
    b += f'<circle cx="680" cy="250" r="78" fill="{SLATE}" opacity=".55"/>' + f'<path d="M690,172 l30,-26 l8,32 z" fill="{SLATE}" opacity=".55"/>'
    b += seg((690, 326), (720, 470), w=60, c="#9AA1A7")
    b += cross(790, 140) + txt(680, 520, "Don't tip the head back", 22, RED, 800, "middle")
    return svg(b)

def front_person(cx, c=SLATE):
    return (dot(cx, 120, 34, c) + f'<rect x="{cx-52}" y="164" width="104" height="170" rx="26" fill="{c}"/>' +
            seg((cx - 58, 182), (cx - 104, 320), c=c, w=24) + seg((cx + 58, 182), (cx + 104, 320), c=c, w=24) +
            seg((cx - 26, 332), (cx - 36, 480), c=c, w=30) + seg((cx + 26, 332), (cx + 36, 480), c=c, w=30))

def heat():
    b = txt(50, 66, "Heat stroke: cool them now", 32, INK, 800)
    cx = 250; b += front_person(cx)
    for x, y in ((cx, 162), (cx - 62, 196), (cx + 62, 196), (cx - 22, 334), (cx + 22, 334)): b += dot(x, y, 18, BLUE)
    b += txt(460, 150, "Best: cold water up to the neck", 26) + "".join(curve(f"M{460+i*58},186 q14,-14 29,0 t29,0", c=BLUE, w=6) for i in range(5))
    b += txt(460, 260, "Otherwise: soak with water and fan.", 24) + txt(460, 300, "Cold packs on the neck,\narmpits and groin.", 24, BLUE, 800)
    b += txt(460, 400, "Keep cooling until they think\nclearly again. Then get help.", 22, DIM, 700)
    b += txt(460, 470, "No drinks if confused.", 22, RED, 800)
    return svg(b)

def hypothermia():
    b = txt(50, 66, "Hypothermia: warm the core first", 32, INK, 800)
    cx = 250; b += front_person(cx)
    b += f'<rect x="{cx-52}" y="164" width="104" height="170" rx="26" fill="{AMBER}" opacity=".85"/>'
    for x, y in ((cx, 150), (cx - 62, 196), (cx + 62, 196), (cx, 334)): b += dot(x, y, 18, RED)
    b += txt(460, 140, "Out of the wind and wet.", 24) + txt(460, 180, "Dry clothes, insulate from\nthe ground, cover the head.", 22, DIM, 700)
    b += txt(460, 280, "Warm chest, neck, armpits\nand groin first.", 24, AMBER, 800) + txt(460, 350, "Blankets, skin-to-skin,\nwarm (not hot) packs.", 22, DIM, 700)
    b += cross(470, 452, 18) + txt(500, 462, "Don't rub arms and legs.", 22, RED, 800)
    b += cross(470, 512, 18) + txt(500, 522, "No alcohol.", 22, RED, 800)
    return svg(b)

DIAGRAMS = {"cpr-adult": cpr, "recovery-position": recovery, "water-treatment": water, "oral-rehydration": ors, "stroke": fast,
            "choking-adult": choking, "choking-infant": choking_infant, "bleeding-pressure": pressure, "tourniquet-placement": tourniquet,
            "tourniquet-improvised": windlass, "splint-sling": splint, "nosebleed": nosebleed, "heat-stroke": heat, "hypothermia": hypothermia}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    for name, fn in DIAGRAMS.items():
        if only and name not in only: continue
        p = f"{OUT}/{name}.svg"; open(p, "w").write(fn())
        if "--png" in sys.argv: subprocess.run(["rsvg-convert", "-w", "900", p, "-o", p[:-4] + ".png"], check=True)
        print(p)
