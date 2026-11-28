#!/usr/bin/env python3
"""Aftergrid feature art, from one source:
  portal/img/icons/<id>.svg     line icons (currentColor) for the Field Mode tiles
  portal/img/tiles/<id>.svg     tile backgrounds: night landscape + contour lines, tinted per feature
  icons/hicolor/scalable/apps/aftergrid-<id>.svg   desktop / menu icons
Run:  python3 content/tools/make_art.py      (then content/tools/render_icons.js for the PNG sizes)
Everything is generated SVG: tiny, crisp at any size, works offline. No stock images, no licences."""
import math, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "../../build/config/includes.chroot"))
PORTAL = f"{ROOT}/usr/share/aftergrid/portal/img"
APPS = f"{ROOT}/usr/share/icons/hicolor/scalable/apps"
AMBER = "#F2A33A"

# 24x24 line glyphs, stroke drawn by the caller
GLYPH = {
 "medical": '<path d="M9 3.5h6v5.5h5.5v6H15v5.5H9V15H3.5V9H9z"/>',
 "water":   '<path d="M12 3c3.6 4.3 6 7.7 6 11a6 6 0 0 1-12 0c0-3.3 2.4-6.7 6-11z"/><path d="M9 15.5a3 3 0 0 0 3 2.5"/>',
 "food":    '<path d="M4 11h16v1.5A7.5 7.5 0 0 1 12.5 20h-1A7.5 7.5 0 0 1 4 12.5z"/><path d="M9 3.5c0 1.6 1.2 1.6 1.2 3.6M14 3.5c0 1.6 1.2 1.6 1.2 3.6"/>',
 "shelter": '<path d="M2.5 20 12 4l9.5 16z"/><path d="M12 4v16M9 20l3-6 3 6"/>',
 "repair":  '<path d="M14.5 3.6a5 5 0 0 0-4.3 6.9l-6.4 6.4a2 2 0 0 0 2.8 2.8l6.4-6.4a5 5 0 0 0 6.9-4.3l-2.9 2.9-3-.8-.8-3z"/>',
 "power":   '<path d="M13.5 2.5 4.5 14h7l-1 7.5 9-11.5h-7z"/>',
 "maps":    '<path d="M3 6.5 9 4l6 2.5L21 4v13.5L15 20l-6-2.5L3 20z"/><path d="M9 4v13.5M15 6.5V20"/>',
 "comms":   '<circle cx="12" cy="11" r="1.6"/><path d="M12 12.6V21M8.5 21h7M8.6 7.6a4.8 4.8 0 0 0 0 6.8M15.4 7.6a4.8 4.8 0 0 1 0 6.8M5.7 4.7a8.9 8.9 0 0 0 0 12.6M18.3 4.7a8.9 8.9 0 0 1 0 12.6"/>',
 "ask":     '<path d="M4 4.5h16v11.5H9.5L4 20.5z"/><path d="M12 7.2l.9 1.9 1.9.9-1.9.9-.9 1.9-.9-1.9-1.9-.9 1.9-.9z"/>',
 "library": '<path d="M4 4h4v16H4zM10 4h4v16h-4z"/><path d="m16.2 5.2 3.8-1 3 15.3-3.8 1z" transform="translate(-1.6 0)"/>',
 "gobag":   '<path d="M6.5 9a5.5 5.5 0 0 1 11 0v11.5h-11z"/><path d="M9.5 6.5V5.5a2.5 2.5 0 0 1 5 0v1M6.5 13.5h11M10 16.5h4"/>',
 "control": '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
 "mesh":    '<circle cx="5" cy="6" r="2"/><circle cx="19" cy="6" r="2"/><circle cx="12" cy="13" r="2"/><circle cx="6" cy="19.5" r="1.6"/><circle cx="18" cy="19.5" r="1.6"/><path d="M6.7 7.1l3.6 4.6M17.3 7.1l-3.6 4.6M7 6h10M10.8 14.6l-3.7 3.7M13.2 14.6l3.7 3.7"/>',
 "field":   '<circle cx="12" cy="12" r="8.5"/><path d="m15.5 8.5-2 5-5 2 2-5z"/>',
 "wiki":    '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z"/>',
 "download":'<path d="M12 3.5v11M7.5 10l4.5 4.5 4.5-4.5"/><path d="M4 15.5v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
 "winlink": '<path d="M3 8.5h13v10H3z"/><path d="m3 8.5 6.5 5 6.5-5M19.5 3v11M17 5.5a3.5 3.5 0 0 1 5 0"/>',
}
# feature -> (hue, label for the scene's character)
HUE = {"medical": 4, "water": 205, "food": 88, "shelter": 168, "repair": 215, "power": 46, "maps": 140,
       "comms": 265, "ask": 32, "library": 24, "gobag": 18, "control": 32, "mesh": 190, "field": 32, "winlink": 230, "wiki": 220, "download": 150}

def hsl(h, s, l): return f"hsl({h} {s}% {l}%)"

def icon_svg(g):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">{GLYPH[g]}</svg>\n')

def ridge(rng, w, base, amp, n=9):
    """A smooth mountain line across the tile as an SVG path (filled to the bottom)."""
    xs = [w * i / n for i in range(n + 1)]
    ys = [base - amp * (0.35 + 0.65 * rng.random()) for _ in xs]
    d = f"M0 {ys[0]:.1f}"
    for i in range(1, len(xs)):
        cx = (xs[i - 1] + xs[i]) / 2
        d += f" C{cx:.1f} {ys[i-1]:.1f} {cx:.1f} {ys[i]:.1f} {xs[i]:.1f} {ys[i]:.1f}"
    return d + f" L{w} 400 L0 400Z"

def contours(rng, w, h, hue):
    """Topographic rings around one or two peaks: the 'map' texture."""
    out = []
    for _ in range(2):
        cx, cy = rng.uniform(w * .45, w * .95), rng.uniform(h * .1, h * .6)
        for k in range(1, 9):
            r = 18 * k + rng.uniform(-4, 4)
            pts = []
            for a in range(0, 361, 15):
                t = math.radians(a); wob = 1 + 0.12 * math.sin(3 * t + k) + 0.06 * math.sin(5 * t)
                pts.append(f"{cx + r * 1.5 * wob * math.cos(t):.1f},{cy + r * wob * math.sin(t):.1f}")
            out.append(f'<polyline points="{" ".join(pts)}"/>')
    return f'<g fill="none" stroke="{hsl(hue, 60, 70)}" stroke-opacity=".10" stroke-width="1">{"".join(out)}</g>'

def tile_svg(g):
    W, H, hue = 640, 400, HUE[g]
    rng = random.Random(g)
    stars = "".join(f'<circle cx="{rng.uniform(0, W):.0f}" cy="{rng.uniform(0, H * .45):.0f}" r="{rng.choice([.6, .8, 1.1])}"/>' for _ in range(38))
    layers = "".join(
        f'<path class="r{i}" d="{ridge(rng, W, H * (0.58 + 0.13 * i), 70 - 14 * i)}" fill="{hsl(hue, 30 - 4 * i, 16 - 3 * i)}"/>'
        for i in range(3))
    big = (f'<g transform="translate({W - 250} 40) scale(9.5)" fill="none" stroke="{hsl(hue, 85, 72)}" stroke-opacity=".16" '
           f'stroke-width=".9" stroke-linecap="round" stroke-linejoin="round">{GLYPH[g]}</g>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice">
<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{hsl(hue, 45, 22)}"/><stop offset=".7" stop-color="{hsl(hue, 30, 11)}"/></linearGradient>
<radialGradient id="glow" cx=".78" cy=".28" r=".55"><stop offset="0" stop-color="{hsl(hue, 90, 60)}" stop-opacity=".35"/><stop offset="1" stop-color="{hsl(hue, 90, 60)}" stop-opacity="0"/></radialGradient></defs>
<rect width="{W}" height="{H}" fill="url(#sky)"/><rect width="{W}" height="{H}" fill="url(#glow)"/>
<g fill="#fff" fill-opacity=".45">{stars}</g>{contours(rng, W, H, hue)}{big}{layers}
</svg>
'''

def app_svg(g):
    hue = HUE[g]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
<defs><linearGradient id="b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{hsl(hue, 22, 21)}"/><stop offset="1" stop-color="{hsl(hue, 18, 9)}"/></linearGradient>
<radialGradient id="h" cx=".3" cy=".15" r=".9"><stop offset="0" stop-color="#fff" stop-opacity=".16"/><stop offset=".55" stop-color="#fff" stop-opacity="0"/></radialGradient>
<linearGradient id="a" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFC56B"/><stop offset="1" stop-color="{AMBER}"/></linearGradient>
<filter id="s" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="6" stdDeviation="7" flood-color="#000" flood-opacity=".45"/></filter>
<pattern id="grid" width="16" height="16" patternUnits="userSpaceOnUse"><path d="M16 0H0V16" fill="none" stroke="#fff" stroke-opacity=".05"/></pattern></defs>
<g filter="url(#s)"><rect x="16" y="14" width="224" height="224" rx="52" fill="url(#b)"/></g>
<rect x="16" y="14" width="224" height="224" rx="52" fill="url(#grid)"/>
<rect x="16" y="14" width="224" height="224" rx="52" fill="url(#h)"/>
<rect x="17" y="15" width="222" height="222" rx="51" fill="none" stroke="#fff" stroke-opacity=".12" stroke-width="2"/>
<rect x="190" y="38" width="22" height="22" rx="5" fill="{AMBER}"/>
<g transform="translate(56 54) scale(6)" fill="none" stroke-linecap="round" stroke-linejoin="round">
<g stroke="{AMBER}" stroke-opacity=".14" stroke-width="4.2">{GLYPH[g]}</g>
<g stroke="url(#a)" stroke-width="1.9">{GLYPH[g]}</g></g>
</svg>
'''

def main():
    for d in (f"{PORTAL}/icons", f"{PORTAL}/tiles", APPS): os.makedirs(d, exist_ok=True)
    for g in GLYPH:
        open(f"{PORTAL}/icons/{g}.svg", "w").write(icon_svg(g))
        open(f"{PORTAL}/tiles/{g}.svg", "w").write(tile_svg(g))
        open(f"{APPS}/aftergrid-{g}.svg", "w").write(app_svg(g))
    print(f"{len(GLYPH)} icons, tiles and app icons written")

if __name__ == "__main__":
    main()
