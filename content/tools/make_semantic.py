#!/usr/bin/env python3
"""Build the meaning-search index for Aftergrid's own books (first-aid cards + field manuals).
Reads the ZIMs, embeds title + opening text of every article with the local embedding server (127.0.0.1:8082),
and writes content/ai/semantic/{vectors.npy, meta.json}. Run after make_zims.py.
"""
import glob, html, json, os, re, sys, urllib.request
import numpy as np
from libzim.reader import Archive

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
ROOT = f"{REPO}/content"
OUT = f"{ROOT}/ai/semantic"
BOOKS = ["aftergrid-firstaid_en", "aftergrid-manuals_en"]
EMBED = "http://127.0.0.1:8082/v1/embeddings"

def text_of(entry):
    h = bytes(entry.get_item().content).decode("utf-8", "ignore")
    h = re.sub(r"(?s)<(style|script)[^>]*>.*?</\1>", " ", h); h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(h)).strip()

def embed(batch):
    req = urllib.request.Request(EMBED, data=json.dumps({"input": batch}).encode(), headers={"Content-Type": "application/json"})
    try: d = json.load(urllib.request.urlopen(req, timeout=600))["data"]
    except urllib.error.HTTPError as e:
        if len(batch) == 1:   # one text too long for the model: keep its first 600 characters
            print("  shortening:", e.read()[:160], flush=True); return embed([batch[0][:600]]) if len(batch[0]) > 600 else (_ for _ in ()).throw(e)
        return [v for t in batch for v in embed([t])]   # retry one at a time
    return [x["embedding"] for x in sorted(d, key=lambda x: x["index"])]

def main():
    meta, texts = [], []
    for name in BOOKS:
        z = sorted(glob.glob(f"{ROOT}/zim/{name}_*.zim"))[-1]; a = Archive(z)
        btitle = a.get_metadata("Title").decode()
        for i in range(a.entry_count):
            e = a.get_entry_by_id(i)
            if e.is_redirect or e.path in ("index",) or not e.get_item().mimetype.startswith("text/html"): continue
            t = text_of(e)
            # cards: whole card (short); manual pages: title + first ~700 characters
            body = t[:1100] if name.endswith("firstaid_en") else t[:700]   # stay under the 512-token limit
            meta.append({"book": name, "book_title": btitle, "path": e.path, "title": e.title})
            texts.append(f"{e.title}. {body}")
    print(len(texts), "entries to embed", flush=True)
    vecs = []
    for s in range(0, len(texts), 4):
        vecs += embed(texts[s:s + 4])
        if s % 160 == 0: print(f"  {s}/{len(texts)}", flush=True)
    V = np.array(vecs, dtype=np.float32); V /= np.linalg.norm(V, axis=1, keepdims=True) + 1e-9
    os.makedirs(OUT, exist_ok=True)
    np.save(f"{OUT}/vectors.npy", V.astype(np.float16)); json.dump(meta, open(f"{OUT}/meta.json", "w"))
    print("wrote", V.shape, OUT)

if __name__ == "__main__": main()
