#!/usr/bin/env python3
"""Build Aftergrid's own library books (ZIM files with a full-text index):
  aftergrid-firstaid_en  - the first-aid cards (content/cards/cards.py)
  aftergrid-manuals_en   - every page of the field manuals (content/library/*/*.pdf), linking back to the PDF page
Usage: make_zims.py firstaid|manuals|all
"""
import html, io, os, re, subprocess, sys
from datetime import date
from libzim.writer import Creator, Item, StringProvider, Hint
from PIL import Image, ImageDraw

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
ROOT = f"{REPO}/content"
OUT = f"{ROOT}/zim"
STAMP = date.today().strftime("%Y-%m")
CSS = """body{font:17px/1.55 system-ui,-apple-system,'Segoe UI',sans-serif;max-width:760px;margin:0 auto;padding:20px;color:#1f1e1c;background:#faf9f5}
h1{font:600 28px/1.25 Georgia,'Source Serif 4',serif;margin:8px 0 4px}.k{color:#8a6a2c;font-size:13px;letter-spacing:.08em;text-transform:uppercase}
ol{padding-left:22px}li{margin:6px 0}.box{border-radius:12px;padding:12px 16px;margin:14px 0}.help{background:#fdecea;border:1px solid #f1b9b2}
.dont{background:#fff6e5;border:1px solid #efd29a}.basis{color:#6b675e;font-size:14px}.aka{color:#8b877d;font-size:13px}
.src{display:inline-block;margin:10px 0;padding:8px 14px;border-radius:999px;background:#f0ece2;color:#3d3929;text-decoration:none}
p{margin:0 0 10px}.pg{white-space:pre-wrap}
figure.dg{margin:14px 0}figure.dg img{width:100%;height:auto;display:block;border-radius:14px}"""

def icon():
    im = Image.new("RGBA", (48, 48), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for r in range(3):
        for c in range(3):
            d.rounded_rectangle([3 + c * 15, 3 + r * 15, 15 + c * 15, 15 + r * 15], 3, fill=(242, 163, 58) if (r, c) == (0, 2) else (58, 68, 76))
    b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()

class Raw(Item):
    def __init__(self, path, data, mime):
        super().__init__(); self.p, self.d, self.m = path, data, mime
    def get_path(self): return self.p
    def get_title(self): return ""
    def get_mimetype(self): return self.m
    def get_contentprovider(self): return StringProvider(self.d)
    def get_hints(self): return {Hint.FRONT_ARTICLE: False}

class Page(Item):
    def __init__(self, path, title, body, front=True):
        super().__init__(); self.p, self.t, self.b, self.f = path, title, body, front
    def get_path(self): return self.p
    def get_title(self): return self.t
    def get_mimetype(self): return "text/html"
    def get_contentprovider(self): return StringProvider(self.b)
    def get_hints(self): return {Hint.FRONT_ARTICLE: self.f}

def page(title, inner):
    return f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{html.escape(title)}</title><style>{CSS}</style></head><body>{inner}</body></html>"

def new_zim(name, title, desc, tags):
    path = f"{OUT}/{name}_{STAMP}.zim"
    for f in os.listdir(OUT):
        if f.startswith(name + "_"): os.remove(f"{OUT}/{f}")
    c = Creator(path).config_indexing(True, "eng")
    return c, path, dict(Name=name, Title=title, Description=desc, Language="eng", Creator="Aftergrid", Publisher="Aftergrid",
                        Date=date.today().isoformat(), Tags=tags)

def meta(c, m):
    for k, v in m.items(): c.add_metadata(k, v)
    c.add_metadata("Illustration_48x48@1", icon())

def firstaid():
    sys.path.insert(0, f"{ROOT}/cards"); from cards import CARDS, CARD_DIAGRAMS, DIAGRAM_ALT
    c, path, m = new_zim("aftergrid-firstaid_en", "Aftergrid First Aid Cards", "Short first-aid protocols for when help is far away", "medical;first aid;aftergrid;_ftindex:yes")
    with c:
        meta(c, m); c.set_mainpath("index")
        links = []
        for d in sorted({d for v in CARD_DIAGRAMS.values() for d in v}):
            c.add_item(Raw(f"diagrams/{d}.svg", open(f"{ROOT}/cards/diagrams/{d}.svg").read(), "image/svg+xml"))
        for x in CARDS:
            figs = "".join(f"<figure class='dg'><img src='diagrams/{d}.svg' alt='{html.escape(DIAGRAM_ALT.get(d, ''))}'></figure>" for d in CARD_DIAGRAMS.get(x["id"], []))
            body = (f"<div class='k'>Aftergrid First Aid Card</div><h1>{html.escape(x['title'])}</h1>" + figs +
                    "<ol>" + "".join(f"<li>{html.escape(s)}</li>" for s in x["steps"]) + "</ol>"
                    f"<div class='box help'><b>Get help urgently:</b> {html.escape(x['help'])}</div>"
                    f"<div class='box dont'><b>Don't:</b> {html.escape(x['dont'])}</div>"
                    f"<p class='basis'>Based on: {html.escape(x['basis'])} Reference only; not a substitute for trained help.</p>"
                    f"<p class='aka'>Also searched as: {html.escape(x['aka'])}</p>")
            c.add_item(Page(x["id"], x["title"], page(x["title"], body)))
            links.append(f"<li><a href='{x['id']}'>{html.escape(x['title'])}</a></li>")
        c.add_item(Page("index", "Aftergrid First Aid Cards", page("First Aid Cards", "<h1>Aftergrid First Aid Cards</h1><ul>" + "".join(links) + "</ul>"), front=False))
    print(path, len(CARDS), "cards")

MANUALS = {  # file stem -> (short title, path id)
    "US-Army-FM-4-25.11-First-Aid": ("Army First Aid (FM 4-25.11)", "fm4-25-11"),
    "ST-31-91B-Special-Forces-Medical-Handbook": ("Special Forces Medical Handbook (ST 31-91B)", "st31-91b"),
    "Emergency-War-Surgery-5th-Ed": ("Emergency War Surgery (5th ed.)", "ews5"),
    "US-Army-ATP-3-50.21-Survival": ("Army Survival (ATP 3-50.21)", "atp3-50-21"),
    "US-Army-FM-21-76-Survival": ("Army Survival (FM 21-76)", "fm21-76"),
    "US-Army-FM-21-10-Field-Hygiene-and-Sanitation": ("Field Hygiene and Sanitation (FM 21-10)", "fm21-10"),
    "Nuclear-War-Survival-Skills-Kearny": ("Nuclear War Survival Skills (Kearny)", "nwss"),
}
OCR = {"ST-31-91B-Special-Forces-Medical-Handbook": f"{REPO}/work/ocr/ST-31-91B"}

def pdf_pages(pdf, stem):
    if stem in OCR and os.path.isdir(OCR[stem]):
        d = OCR[stem]; n = len([f for f in os.listdir(d) if re.fullmatch(r"p\d+\.txt", f)])
        return [open(f"{d}/p{i}.txt", errors="ignore").read() for i in range(1, n + 1)]
    return subprocess.run(["pdftotext", "-enc", "UTF-8", pdf, "-"], capture_output=True, text=True).stdout.split("\f")

def heading(text, short):
    for ln in text.splitlines()[:14]:
        s = ln.strip(" .-\t")
        if 6 <= len(s) <= 80 and len(re.findall(r"[A-Za-z]{3,}", s)) >= 2 and not re.search(r"\b(FM|ATP|ST)\s*\d|^\d+\s*$|Page \d|distribution|unlimited", s, re.I):
            return re.sub(r"\s+", " ", s)[:70]
    return ""

def manuals():
    c, path, m = new_zim("aftergrid-manuals_en", "Field Manuals (searchable)", "Every page of the US Army and survival field manuals on this Aftergrid, searchable", "medical;survival;manuals;aftergrid;_ftindex:yes")
    n = 0
    with c:
        meta(c, m); c.set_mainpath("index"); toc = []
        for cat in ("medical", "survival"):
            for f in sorted(os.listdir(f"{ROOT}/library/{cat}")):
                stem = f[:-4]
                if stem not in MANUALS: continue
                short, pid = MANUALS[stem]; pages = pdf_pages(f"{ROOT}/library/{cat}/{f}", stem); kept = 0
                for i, t in enumerate(pages, 1):
                    t = t.replace("\x0c", "").strip()
                    if len(re.findall(r"[A-Za-z]{3,}", t)) < 40: continue
                    h = heading(t, short)
                    title = f"{short}, p. {i}" + (f": {h}" if h else "")
                    paras = [re.sub(r"\s*\n\s*", " ", p).strip() for p in re.split(r"\n\s*\n", t) if p.strip()]
                    body = (f"<div class='k'>{html.escape(short)} · page {i}</div><h1>{html.escape(h or short)}</h1>"
                            f"<a class='src' href='/files/baked/library/{cat}/{f}#page={i}'>Open page {i} of the original PDF</a>"
                            + "".join(f"<p>{html.escape(p)}</p>" for p in paras))
                    c.add_item(Page(f"{pid}/p{i:03d}", title, page(title, body))); kept += 1; n += 1
                toc.append(f"<li>{html.escape(short)}: {kept} pages</li>")
        c.add_item(Page("index", "Field Manuals", page("Field Manuals", "<h1>Field Manuals (searchable)</h1><ul>" + "".join(toc) + "</ul>"), front=False))
    print(path, n, "pages")

if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("firstaid", "all"): firstaid()
    if what in ("manuals", "all"): manuals()
