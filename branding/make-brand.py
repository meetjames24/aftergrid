#!/usr/bin/env python3
"""Generate every Aftergrid brand asset from code (re-run to rebuild them all).

Mark: a 3x3 grid gone dark with one cell still lit amber: the light that stays on
after the grid fails.
Palette: night slate #14171A, signal amber #F2A33A, bone white #E9ECEF.
"""
import os, subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
INC = os.path.join(HERE, "..", "build", "config", "includes.chroot")
OUT = os.path.join(INC, "usr/share/aftergrid/branding")
os.makedirs(OUT, exist_ok=True)
SLATE, SLATE2, AMBER, BONE, LINE = "#14171A", "#1C2126", "#F2A33A", "#E9ECEF", "#262D33"
TAG = "WHEN THE GRID GOES DOWN, AFTERGRID BOOTS UP"

def mark(x=0, y=0, s=1.0, lit=AMBER, dim="#3A444C"):
    """The Aftergrid mark in a 256x256 box: a 3x3 grid gone dark, one cell still lit."""
    t = f'translate({x},{y}) scale({s})'
    cells = []
    for r in range(3):
        for c in range(3):
            on = (r, c) == (0, 2)
            cells.append(f'<rect x="{24 + c*76}" y="{24 + r*76}" width="56" height="56" rx="10" fill="{lit if on else dim}"/>')
    return f'<g transform="{t}">' + "".join(cells) + '</g>'

def svg(w, h, body, bg=None):
    b = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{b}{body}</svg>'

def render(svgtext, name, w=None, h=None):
    p = os.path.join(OUT, name)
    open(p.replace(".png", ".svg"), "w").write(svgtext)
    cmd = ["rsvg-convert", p.replace(".png", ".svg"), "-o", p] + (["-w", str(w)] if w else []) + (["-h", str(h)] if h else [])
    subprocess.check_call(cmd)
    return p

def wordmark(x, y, size, color=BONE, spacing=0.14):
    return (f'<text x="{x}" y="{y}" font-family="Archivo Black" font-size="{size}" fill="{color}" '
            f'letter-spacing="{size*spacing:.1f}">AFTERGRID</text>')

def tagline(x, y, size, anchor="start", color="#9AA4AD"):
    return (f'<text x="{x}" y="{y}" font-family="Inter Display" font-weight="600" font-size="{size}" fill="{color}" '
            f'letter-spacing="{size*0.28:.1f}" text-anchor="{anchor}">{TAG}</text>')

# 1. Mark alone (icons, favicon)
m = svg(256, 256, mark())
open(os.path.join(OUT, "aftergrid-mark.svg"), "w").write(m)
for s in (512, 256, 128, 64, 48, 32, 16):
    subprocess.check_call(["rsvg-convert", os.path.join(OUT, "aftergrid-mark.svg"), "-w", str(s), "-h", str(s), "-o", os.path.join(OUT, f"aftergrid-mark-{s}.png")])
# rounded app icon (mark on slate tile)
render(svg(256, 256, f'<rect x="8" y="8" width="240" height="240" rx="52" fill="{SLATE}"/>' + mark(38, 34, 0.7)), "aftergrid-icon.png", 256, 256)

# 2. Horizontal lockup: mark + wordmark (+ tagline)
render(svg(1700, 300, mark(0, 22, 1.0) + wordmark(300, 205, 170)), "aftergrid-lockup.png", 1700)
render(svg(1700, 380, mark(0, 22, 1.0) + wordmark(300, 205, 170) + tagline(304, 330, 30)), "aftergrid-lockup-tag.png", 1700)
# Stacked: mark over wordmark (boot splash, installer)
render(svg(1000, 520, mark(372, 0, 1.0) + wordmark(500 + 130*0.07, 430, 130).replace('<text ', '<text text-anchor="middle" ')), "aftergrid-stacked.png", 1000)

# 3. Topographic background (contours of smooth random terrain)
LIGHT = ("#FAF9F5", "#EFEBE1", "#E4DECF", "#D6CEBB")   # paper top, paper bottom, contour, major contour
DARK = (SLATE2, SLATE, LINE, "#323b42")
def topo(w, h, seed=7, levels=22, pal=None):
    pal = pal or DARK
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:1:h * 1j / 4, 0:w / h:w * 1j / 4]
    z = np.zeros_like(xx)
    for _ in range(26):
        cx, cy = rng.uniform(0, w / h), rng.uniform(0, 1)
        sx = rng.uniform(0.08, 0.35)
        z += rng.uniform(-1, 1) * np.exp(-(((xx - cx) ** 2) + ((yy - cy) ** 2)) / (2 * sx ** 2))
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    g = np.linspace(0, 1, 256)
    ax.imshow(np.outer(np.ones(256), g) * 0 + np.outer(g, np.ones(256)), extent=[0, w / h, 0, 1], cmap=matplotlib.colors.LinearSegmentedColormap.from_list("bg", [pal[0], pal[1]]), aspect="auto", origin="lower")
    cs = ax.contour(xx, yy, z, levels=levels, colors=pal[2], linewidths=1.1 * w / 1920, linestyles="solid")
    ax.contour(xx, yy, z, levels=cs.levels[::5], colors=pal[3], linewidths=1.8 * w / 1920, linestyles="solid")
    ax.set_xlim(0, w / h); ax.set_ylim(0, 1)
    p = os.path.join(OUT, f"_topo-{w}x{h}-{pal[0][1:]}.png"); fig.savefig(p, dpi=100); plt.close(fig)
    return p

def compose(w, h, name, overlay, pal=None):
    t = topo(w, h, pal=pal)
    body = f'<image href="file://{t}" width="{w}" height="{h}"/>' + overlay
    render(svg(w, h, body), name, w, h)
    os.remove(os.path.join(OUT, name.replace(".png", ".svg")))   # references a temp file

# 4. Desktop wallpaper: lockup bottom-left, quiet
for (w, h) in ((3840, 2160), (1920, 1080)):
    k = w / 1920
    compose(w, h, f"wallpaper-{w}x{h}.png",
            mark(110 * k, h - 300 * k, 0.62 * k) + wordmark(300 * k, h - 166 * k, 92 * k) + tagline(305 * k, h - 112 * k, 17 * k))

# 4b. Light desktop wallpaper (default: the desktop and Field Mode ship light); the dark one becomes the Night variant
for (w, h) in ((3840, 2160), (1920, 1080)):
    k = w / 1920
    compose(w, h, f"wallpaper-light-{w}x{h}.png",
            mark(110 * k, h - 300 * k, 0.62 * k) + wordmark(300 * k, h - 166 * k, 92 * k, color="#1F1E1C") + tagline(305 * k, h - 112 * k, 17 * k, color="#8A857A"), pal=LIGHT)

# 5. Boot menu (GRUB) background: lockup centered top, menu sits in the lower half
compose(1920, 1080, "grub-1920x1080.png",
        mark(840, 120, 0.94) + wordmark(960 + 110*0.07, 470, 110).replace('<text ', '<text text-anchor="middle" ') + tagline(960 + 20*0.14, 520, 20, "middle"))

# 6. Login / lock screen background = wallpaper; boot splash logo = stacked mark (transparent)
for f in os.listdir(OUT):
    if f.startswith("_topo"): os.remove(os.path.join(OUT, f))
print("brand assets:", sorted(os.listdir(OUT)))

# 7. Deploy into every place the OS shows the brand
import shutil
C = os.path.join(HERE, "..", "build", "config")
def cp(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copyfile(os.path.join(OUT, src), dst)
def conv(src, dst, w):
    os.makedirs(os.path.dirname(dst), exist_ok=True); subprocess.check_call(["rsvg-convert", os.path.join(OUT, src), "-w", str(w), "-o", dst])
cp("grub-1920x1080.png", f"{C}/bootloaders/grub-pc/splash.png")
conv("aftergrid-stacked.svg", f"{INC}/usr/share/plymouth/themes/aftergrid/logo.png", 300)
conv("aftergrid-stacked.svg", f"{INC}/usr/share/plasma/look-and-feel/org.aftergrid.desktop/contents/splash/images/aftergrid.png", 480)
# Plasma picks images/ for light colour schemes and images_dark/ for dark ones
cp("wallpaper-light-3840x2160.png", f"{INC}/usr/share/wallpapers/Aftergrid/contents/images/3840x2160.png")
cp("wallpaper-light-1920x1080.png", f"{INC}/usr/share/wallpapers/Aftergrid/contents/images/1920x1080.png")
cp("wallpaper-3840x2160.png", f"{INC}/usr/share/wallpapers/Aftergrid/contents/images_dark/3840x2160.png")
cp("wallpaper-1920x1080.png", f"{INC}/usr/share/wallpapers/Aftergrid/contents/images_dark/1920x1080.png")
for sz in (16, 32, 48, 64, 128, 256, 512):
    cp(f"aftergrid-mark-{sz}.png", f"{INC}/usr/share/icons/hicolor/{sz}x{sz}/apps/aftergrid-os.png")
cp("aftergrid-mark.svg", f"{INC}/usr/share/icons/hicolor/scalable/apps/aftergrid-os.svg")
cp("aftergrid-mark-256.png", f"{INC}/etc/calamares/branding/aftergrid/aftergrid-logo.png")
conv("aftergrid-lockup-tag.svg", f"{INC}/etc/calamares/branding/aftergrid/welcome.png", 640)
cp("aftergrid-mark.svg", f"{INC}/usr/share/aftergrid/portal/aftergrid-mark.svg")
cp("aftergrid-mark-32.png", f"{INC}/usr/share/aftergrid/portal/favicon.ico")
print("deployed")
