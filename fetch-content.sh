#!/bin/bash
# Get everything the ISO build needs that is too big for git. Safe to re-run: finished files are
# skipped, partial downloads resume.
#   ./fetch-content.sh          all of it
#   ./fetch-content.sh ai       only llama.cpp + AI models
# Steps: AI (models; llama.cpp/pmtiles/pat via build-tools.sh) -> library ZIMs -> field manuals (+OCR)
#        -> Aftergrid's own ZIMs -> built-in maps -> meaning-search index -> Claude + Chrome packages
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
C="$HERE/content"; INC="$HERE/build/config/includes.chroot"
mkdir -p "$C"/{zim,maps,library/survival,library/medical,models/qwen3-4b,models/embed,ai/semantic}
cd "$C"
FAILED=0
get(){ [ -s "$2" ] && [ ! -e "$2.part" ] && { echo "HAVE $2"; return 0; }
       mkdir -p "$(dirname "$2")"
       curl -fL --retry 5 -C - -o "$2.part" "$1" && mv "$2.part" "$2" && echo "OK $2" || { echo "FAIL $2"; FAILED=1; }; }
K=https://download.kiwix.org/zim
kiwix(){ # newest ZIM: kiwix <dir> <prefix>, with checksum
  local f; f=$(curl -fsSL "$K/$1/" | grep -o "href=\"$2_[0-9]\{4\}-[0-9]\{2\}\.zim\"" | cut -d'"' -f2 | sort | tail -1)
  [ -n "$f" ] || { echo "FAIL no ZIM for $2"; FAILED=1; return; }
  ls zim/"$2"_*.zim 2>/dev/null | grep -v "/$f$" | xargs -r rm -f          # drop older editions
  get "$K/$1/$f" "zim/$f"
  [ -f "zim/$f.ok" ] && return
  local want have; want=$(curl -fsSL "$K/$1/$f.sha256" | awk '{print $1}'); have=$(sha256sum "zim/$f" | awk '{print $1}')
  [ "$want" = "$have" ] && { echo "SHA OK $f"; touch "zim/$f.ok"; } || { echo "SHA BAD $f"; rm -f "zim/$f"; FAILED=1; }
}

# ---- offline AI --------------------------------------------------------------
HF=https://huggingface.co
get "$HF/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen3-4B-Instruct-2507-Q4_K_M.gguf" models/qwen3-4b/Qwen3-4B-Instruct-2507-Q4_K_M.gguf
get "$HF/CompendiumLabs/bge-small-en-v1.5-gguf/resolve/main/bge-small-en-v1.5-q8_0.gguf" models/embed/bge-small-en-v1.5-q8_0.gguf
# llama.cpp, pmtiles and Pat are compiled from source in a Debian 13 chroot (no GitHub downloads)
if [ -z "${SKIP_TOOLS:-}" ] && { [ ! -x "$INC/opt/llama/bin/llama-server" ] || [ ! -x "$INC/usr/local/bin/pmtiles" ] || [ ! -x "$INC/usr/local/bin/pat" ]; }; then
  "$HERE/build-tools.sh" || { echo "FAIL build-tools.sh"; FAILED=1; }
fi
[ "${1:-}" = ai ] && exit $FAILED

# ---- library -----------------------------------------------------------------
kiwix other zimgit-water_en;  kiwix other zimgit-medicine_en;  kiwix other zimgit-food-preparation_en
kiwix other zimgit-knots_en;  kiwix other zimgit-post-disaster_en
kiwix other appropedia_en_all_maxi;  kiwix other mdwiki_en_all_maxi
kiwix wikipedia wikipedia_el_all_mini

# ---- field manuals (public domain) -------------------------------------------
A=https://archive.org/download
get "$A/survival-atp-3-50-21/Survival%20%28ATP%203-50-21%29.pdf" library/survival/US-Army-ATP-3-50.21-Survival.pdf
get "$A/Fm21-76SurvivalManual/FM21-76_SurvivalManual.pdf" library/survival/US-Army-FM-21-76-Survival.pdf
get "$A/FM21-10_2000/FM21-10_2000.pdf" library/survival/US-Army-FM-21-10-Field-Hygiene-and-Sanitation.pdf
get "$A/NuclearWarSurvivalSkills_201311/Nuclear%20War%20Survival%20Skills.pdf" library/survival/Nuclear-War-Survival-Skills-Kearny.pdf
get "$A/FM4-25.11/FM4-25.11.pdf" library/medical/US-Army-FM-4-25.11-First-Aid.pdf
get "$A/ST_31-91B_Special_Forces_Medical_Handbook/ST_31-91B_Special_Forces_Medical_Handbook.pdf" library/medical/ST-31-91B-Special-Forces-Medical-Handbook.pdf
get "$A/ews5man-mil/ews5man.pdf" library/medical/Emergency-War-Surgery-5th-Ed.pdf
# ST 31-91B is a scan: OCR it once so its pages are searchable (needs tesseract-ocr + poppler-utils)
O="$HERE/work/ocr/ST-31-91B"; PDF=library/medical/ST-31-91B-Special-Forces-Medical-Handbook.pdf
if [ -f "$PDF" ] && [ ! -f "$O/done" ] && command -v tesseract >/dev/null; then
  echo "OCR $PDF (a few minutes)"; mkdir -p "$O"
  N=$(pdfinfo "$PDF" | awk '/^Pages:/{print $2}')
  # one Tesseract thread per page, one page per CPU (Tesseract's own threading oversubscribes badly)
  seq 1 "$N" | OMP_THREAD_LIMIT=1 xargs -P "$(nproc)" -I{} sh -c "[ -s '$O/p{}.txt' ] || { pdftoppm -f {} -l {} -r 200 -gray -png '$PDF' '$O/img{}' && tesseract \$(ls '$O'/img{}*.png | head -1) '$O/p{}' >/dev/null 2>&1; rm -f '$O'/img{}*.png; }"
  [ "$(ls "$O"/p*.txt 2>/dev/null | wc -l)" -ge "$N" ] && touch "$O/done" || { echo "FAIL OCR incomplete"; FAILED=1; }
fi

# ---- Aftergrid's own books: first-aid cards + every manual page, searchable --
python3 "$C/tools/make_zims.py" all || { echo "FAIL make_zims.py (needs: pip install libzim)"; FAILED=1; }

# ---- built-in maps -------------------------------------------------------------
PM="$INC/usr/local/bin/pmtiles"
if [ -x "$PM" ]; then
  W=""; for i in $(seq 0 14); do d=$(date -u -d "-$i day" +%Y%m%d)
    curl -fsI "https://build.protomaps.com/$d.pmtiles" >/dev/null 2>&1 && { W="https://build.protomaps.com/$d.pmtiles"; break; }; done
  #    name      bbox (W,S,E,N)               max zoom
  for m in "world    -180,-85,180,85           6" \
           "greece   19.3,34.7,29.7,41.8      11" \
           "crete    23.4,34.8,26.4,35.8      14" \
           "arkansas -94.7,33.0,-89.6,36.5    13"; do
    read -r n b z <<<"$m"
    [ -s "maps/$n.pmtiles" ] && { echo "HAVE maps/$n.pmtiles"; continue; }
    [ -n "$W" ] && "$PM" extract "$W" "maps/$n.pmtiles.part" --bbox="$b" --maxzoom="$z" && mv "maps/$n.pmtiles.part" "maps/$n.pmtiles" \
      && echo "OK maps/$n.pmtiles" || { echo "FAIL map $n"; FAILED=1; }
  done
fi

# ---- meaning-based search index over the cards + manuals ------------------------
# llama-server is built for Debian 13, so it runs inside build-tools.sh's chroot (any host distro works)
TC="$HERE/work/tools-chroot"
if [ ! -s ai/semantic/vectors.npy ] && [ -x "$TC/opt/llama/bin/llama-server" ]; then
  [ "$(id -u)" = 0 ] || { echo "FAIL meaning-search index needs root (chroot): sudo ./fetch-content.sh"; exit 1; }
  for d in proc sys dev; do mountpoint -q "$TC/$d" || mount --bind /$d "$TC/$d"; done
  mkdir -p "$TC/models"; cp -f models/embed/bge-small-en-v1.5-q8_0.gguf "$TC/models/"
  chroot "$TC" /opt/llama/bin/llama-server -m /models/bge-small-en-v1.5-q8_0.gguf --host 127.0.0.1 --port 8082 \
     --embedding --pooling cls -c 2048 -ub 512 -b 2048 --no-webui >"$HERE/work/embed.log" 2>&1 & E=$!
  for i in $(seq 60); do curl -sf http://127.0.0.1:8082/health >/dev/null && break; sleep 1; done
  python3 "$C/tools/make_semantic.py" || { echo "FAIL make_semantic.py"; FAILED=1; }
  kill $E 2>/dev/null
fi

# ---- packages that aren't in Debian: Claude desktop, Claude Code, Chrome ---------
P="$HERE/build/config/packages.chroot"; mkdir -p "$P"
deb(){ # deb <apt repo base> <package>
  local f; f=$(curl -fsSL "$1/dists/stable/main/binary-amd64/Packages" | awk -v p="$2" '$1=="Package:"{x=($2==p)} x&&$1=="Filename:"{print $2}' | tail -1)
  [ -n "$f" ] && get "$1/$f" "$P/$(basename "$f")" || { echo "FAIL $2 package"; FAILED=1; }; }
ls "$P"/claude-desktop_*.deb >/dev/null 2>&1 || deb https://downloads.claude.ai/claude-desktop/apt/stable claude-desktop
ls "$P"/claude-code_*.deb    >/dev/null 2>&1 || deb https://downloads.claude.ai/claude-code/apt/stable claude-code
get https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb "$P/google-chrome-stable_current_amd64.deb"

[ $FAILED = 0 ] && echo ALLDONE || echo "SOME STEPS FAILED (re-run to resume)"
exit $FAILED
