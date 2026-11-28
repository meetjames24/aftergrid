#!/bin/bash
# Build an Aftergrid ISO.
#   ./build-aftergrid.sh [full|standard|lite]     (default: full)
#
# 1. live-build makes the base system ISO (OS + apps + portal, no big content).
# 2. The offline library for the chosen profile is added to the ISO file system
#    at /aftergrid-library (read straight from the stick at runtime, not copied into RAM).
#
# Profiles (content under ./content):
#   lite      survival packs, manuals, maps
#   standard  lite + WikiMed + Appropedia
#   full      standard + offline AI model (Qwen3 4B)
set -euo pipefail
PROFILE="${1:-full}"
VER="1.1"
HERE="$(cd "$(dirname "$0")" && pwd)"
B="$HERE/build"; CONTENT="$HERE/content"; STAGE="$HERE/stage"; OUT="$HERE/out"

case "$PROFILE" in
  lite)     ZIMS="aftergrid-* zimgit-* wikipedia_el_all_mini_*"; MODELS="";;
  standard) ZIMS="aftergrid-* zimgit-* mdwiki_* appropedia_* wikipedia_el_all_mini_*"; MODELS="";;
  full)     ZIMS="aftergrid-* zimgit-* mdwiki_* appropedia_* wikipedia_el_all_mini_*"; MODELS="qwen3-4b";;
  *) echo "profile must be full, standard or lite"; exit 1;;
esac

echo "== 0/3 preflight"
miss=0
need(){ ls $1 >/dev/null 2>&1 || { echo "MISSING: $1  ($2)"; miss=1; }; }
need "$B/config/includes.chroot/opt/llama/bin/llama-server" "./fetch-content.sh ai"
need "$CONTENT/models/embed/*.gguf" "./fetch-content.sh ai"
for m in $MODELS; do need "$CONTENT/models/$m/*.gguf" "./fetch-content.sh ai"; done
[ $miss = 0 ] || { echo "Without these the offline AI will not start on the stick. Stopping."; exit 1; }

echo "== 1/3 base system (live-build)"
cd "$B"
if [ -n "${REUSE_BASE:-}" ] && [ -f "$B/aftergrid-amd64.hybrid.iso" ]; then echo "(REUSE_BASE: keeping the existing base system)"; else
lb clean >/dev/null 2>&1 || true
lb config >/dev/null
lb build 2>&1 | tee "$HERE/build.log" | grep -E "^P: |^E: " || true
[ -f "$B/aftergrid-amd64.hybrid.iso" ] || { echo "base build failed: see build.log"; exit 1; }
rm -rf "$B/chroot"            # free disk space before remastering
fi
BASE="$B/aftergrid-amd64.hybrid.iso"

echo "== 2/3 staging '$PROFILE' library"
rm -rf "$STAGE"; mkdir -p "$STAGE/aftergrid-library"/{zim,maps,library,models}
# (patterns are expanded inside content/zim only: unquoted, they used to match files in the build folder)
set -f; ZARR=($ZIMS); set +f
for pat in "${ZARR[@]}"; do
  ls "$CONTENT"/zim/$pat.zim >/dev/null 2>&1 || { echo "MISSING library book: content/zim/$pat.zim (run ./fetch-content.sh)"; exit 1; }
  cp -al "$CONTENT"/zim/$pat.zim "$STAGE/aftergrid-library/zim/"          # .zim only (not checksum markers)
done
cp -al "$CONTENT"/maps/*.pmtiles "$STAGE/aftergrid-library/maps/"
cp -al "$CONTENT"/library/. "$STAGE/aftergrid-library/library/"
for m in $MODELS; do cp -al "$CONTENT/models/$m" "$STAGE/aftergrid-library/models/"; done
# every edition: the small embedding model (~37 MB) and the meaning-search index for the cards and manuals
cp -al "$CONTENT/models/embed" "$STAGE/aftergrid-library/models/"
mkdir -p "$STAGE/aftergrid-library/ai" && cp -al "$CONTENT/ai/semantic" "$STAGE/aftergrid-library/ai/"
# overlay kit: turns Debian / Raspberry Pi OS (x86_64 or arm64) into Aftergrid
mkdir -p "$STAGE/aftergrid-library/overlay"
tar -czf "$STAGE/aftergrid-library/overlay/aftergrid-overlay.tar.gz" -C "$B/config/includes.chroot" --exclude=./opt/aftergrid/wheels .
cp "$B/config/includes.chroot/usr/share/aftergrid/overlay/aftergrid-overlay-install.sh" "$STAGE/aftergrid-library/overlay/"
du -sh "$STAGE/aftergrid-library"

echo "== 3/3 writing ISO"
mkdir -p "$OUT"; N="Aftergrid-$VER-$PROFILE.iso"; ISO="$OUT/$N"; rm -f "$ISO"
if [ "${SPLIT:-1}" = 1 ]; then
  # Stream straight into 380 MB delivery parts (no second full-size copy on disk).
  rm -rf "$OUT/parts"; mkdir -p "$OUT/parts"
  xorriso -indev "$BASE" -outdev stdio:/dev/fd/1 -map "$STAGE/aftergrid-library" /aftergrid-library -boot_image any replay 2>"$OUT/xorriso.log" \
    | tee >(sha256sum | sed "s|-|$N|" > "$ISO.sha256") \
    | split -b 380M -d -a 2 --additional-suffix=.part - "$OUT/parts/$N."
  sleep 2; tail -2 "$OUT/xorriso.log"
  H=$(cut -d' ' -f1 "$ISO.sha256" | tr a-f A-F)
  SIZES=$(cd "$OUT/parts" && for f in "$N".*.part; do n=${f#$N.}; n=${n%.part}; printf "'%s'=%s; " "$n" "$(stat -c %s "$f")"; done)
  sed -e "s|@ISONAME@|$N|g" -e "s|@HASH@|$H|g" -e "s|@SIZES@|${SIZES%; }|" "$HERE/flasher/flash-aftergrid.ps1" | sed 's/$/\r/' > "$OUT/parts/flash-aftergrid.ps1"
  printf '@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%%~dp0flash-aftergrid.ps1"\r\n' > "$OUT/parts/FLASH-Aftergrid.bat"
  printf '@echo off\r\npowershell -NoProfile -ExecutionPolicy Bypass -File "%%~dp0flash-aftergrid.ps1" -ListOnly\r\n' > "$OUT/parts/LIST-USB.bat"
  # Aftergrid USB Maker (Windows): the program plus a manifest of the parts it writes and checks
  # ... and the online catalog (out/latest.json) the one-file USB Maker reads when no image sits next to it.
  #   Upload out/latest.json + the .part files; RELEASE_BASE = where the parts live (default: same folder).
  python3 - "$OUT/parts" "$N" "$H" "$PROFILE" "${RELEASE_BASE:-}" "$OUT/latest.json" <<'PY'
import json, os, sys
d, name, sha, profile, base, cat = sys.argv[1:7]
parts = sorted(f for f in os.listdir(d) if f.startswith(name + ".") and f.endswith(".part"))
size = sum(os.path.getsize(os.path.join(d, f)) for f in parts)
json.dump({"name": name, "size": size, "sha256": sha,
           "parts": [{"file": f} for f in parts]}, open(os.path.join(d, "aftergrid-image.json"), "w"), indent=1)
TITLES = {"lite": "Lite: survival library + maps", "standard": "Standard: + WikiMed + Appropedia",
          "full": "Full: everything + offline AI (recommended)"}
ed = {"id": profile, "title": TITLES.get(profile, profile), "name": name, "size": size, "sha256": sha,
      "parts": [{"url": base + f, "size": os.path.getsize(os.path.join(d, f))} for f in parts]}
c = json.load(open(cat)) if os.path.exists(cat) else {"editions": []}
c["editions"] = sorted([e for e in c["editions"] if e["id"] != profile] + [ed], key=lambda e: e["size"])
json.dump(c, open(cat, "w"), indent=1); print("catalog:", cat, [e["id"] for e in c["editions"]])
PY
  cp "$HERE/flasher/usbmaker/Aftergrid USB Maker.exe" "$OUT/parts/"
  printf 'Aftergrid USB Maker\r\n\r\n1. Keep every file in this folder together.\r\n2. Plug in a USB stick (16 GB or larger). It will be erased.\r\n3. Double-click "Aftergrid USB Maker.exe" and follow the steps.\r\n\r\nIt writes the stick, then reads it back and checks every byte.\r\n' > "$OUT/parts/READ ME FIRST.txt"
  cat "$ISO.sha256"; echo "$(ls "$OUT/parts"/*.part | wc -l) parts, $(du -ch "$OUT/parts"/*.part | tail -1 | cut -f1) total"
else
  xorriso -indev "$BASE" -outdev "$ISO" -map "$STAGE/aftergrid-library" /aftergrid-library -boot_image any replay 2>&1 | tail -3
  ( cd "$OUT" && sha256sum "$N" > "$N.sha256" ); ls -la "$ISO"; cat "$ISO.sha256"
fi
