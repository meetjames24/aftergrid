#!/bin/bash
# Download everything the ISO build needs that is too big for git:
#   library (ZIMs, manuals), llama.cpp binaries (/opt/llama), the AI models.
#   ./fetch-content.sh            all of it
#   ./fetch-content.sh ai         only llama.cpp + models
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
C="$HERE/content"; mkdir -p "$C"/{zim,manuals/survival,manuals/medical,models/qwen3-4b,models/embed}
cd "$C"
get(){ [ -s "$2" ] && [ ! -e "$2.part" ] && { echo "HAVE $2"; return 0; }
       curl -fL --retry 5 -C - -o "$2.part" "$1" && mv "$2.part" "$2" && echo "OK $2" || { echo "FAIL $2"; FAILED=1; }; }
FAILED=0

# ---- offline AI ------------------------------------------------------------
HF=https://huggingface.co
get "$HF/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen3-4B-Instruct-2507-Q4_K_M.gguf" models/qwen3-4b/Qwen3-4B-Instruct-2507-Q4_K_M.gguf
get "$HF/CompendiumLabs/bge-small-en-v1.5-gguf/resolve/main/bge-small-en-v1.5-q8_0.gguf" models/embed/bge-small-en-v1.5-q8_0.gguf

# llama.cpp: latest Linux x64 build with Vulkan (uses a GPU when there is one, CPU otherwise)
LL="$HERE/build/config/includes.chroot/opt/llama"
if [ ! -x "$LL/bin/llama-server" ]; then
  URL=$(curl -fsSL https://api.github.com/repos/ggml-org/llama.cpp/releases/latest \
        | grep -o '"browser_download_url": *"[^"]*bin-ubuntu-vulkan-x64[^"]*"' | head -1 | cut -d'"' -f4)
  if [ -n "$URL" ]; then
    T=$(mktemp -d); curl -fL --retry 5 -o "$T/l.zip" "$URL" && (cd "$T" && unzip -q l.zip)
    mkdir -p "$LL/bin"; S=$(dirname "$(find "$T" -name llama-server -type f | head -1)")
    cp -a "$S"/. "$LL/bin/"; chmod +x "$LL/bin"/llama-*; rm -rf "$T"
    "$LL/bin/llama-server" --version 2>&1 | head -1; echo "OK llama.cpp $(basename "$URL")"
  else echo "FAIL llama.cpp (no release found)"; FAILED=1; fi
else echo "HAVE llama.cpp"; fi
[ "${1:-}" = ai ] && exit $FAILED

# ---- library ---------------------------------------------------------------
K=https://download.kiwix.org/zim
for f in other/zimgit-water_en_2024-08.zim other/zimgit-medicine_en_2024-08.zim other/zimgit-food-preparation_en_2025-04.zim other/zimgit-knots_en_2024-08.zim other/zimgit-post-disaster_en_2024-05.zim other/appropedia_en_all_maxi_2026-02.zim other/mdwiki_en_all_maxi_2025-11.zim; do
  n=$(basename $f); get $K/$f zim/$n
  want=$(curl -fsSL $K/$f.sha256 | awk '{print $1}'); have=$(sha256sum zim/$n | awk '{print $1}'); [ "$want" = "$have" ] && echo "SHA OK $n" || { echo "SHA BAD $n"; FAILED=1; }
done
A=https://archive.org/download
get "$A/survival-atp-3-50-21/Survival%20%28ATP%203-50-21%29.pdf" manuals/survival/US-Army-ATP-3-50.21-Survival.pdf
get "$A/Fm21-76SurvivalManual/FM21-76_SurvivalManual.pdf" manuals/survival/US-Army-FM-21-76-Survival.pdf
get "$A/FM21-10_2000/FM21-10_2000.pdf" manuals/survival/US-Army-FM-21-10-Field-Hygiene-and-Sanitation.pdf
get "$A/FM4-25.11/FM4-25.11.pdf" manuals/medical/US-Army-FM-4-25.11-First-Aid.pdf
get "$A/ST_31-91B_Special_Forces_Medical_Handbook/ST_31-91B_Special_Forces_Medical_Handbook.pdf" manuals/medical/ST-31-91B-Special-Forces-Medical-Handbook.pdf
get "$A/ews5man-mil/ews5man.pdf" manuals/medical/Emergency-War-Surgery-5th-Ed.pdf
get "$A/NuclearWarSurvivalSkills_201311/Nuclear%20War%20Survival%20Skills.pdf" manuals/survival/Nuclear-War-Survival-Skills-Kearny.pdf
[ $FAILED = 0 ] && echo ALLDONE || echo "SOME DOWNLOADS FAILED (re-run to resume)"
exit $FAILED
