#!/bin/bash
# Upload a built ISO edition to the GitHub Release for a tag (after ./build-aftergrid.sh).
#   ./release.sh v1.1            uploads out/parts/*.part + out/latest.json (+ checksums)
# Needs the GitHub CLI logged in (gh auth login). Run once per edition you build; latest.json
# collects every edition, so build lite/standard/full first, then run this once.
set -euo pipefail
TAG="${1:?usage: ./release.sh <tag, e.g. v1.1>}"
OUT="$(cd "$(dirname "$0")" && pwd)/out"
[ -f "$OUT/latest.json" ] || { echo "no out/latest.json: run ./build-aftergrid.sh first"; exit 1; }
gh release view "$TAG" >/dev/null 2>&1 || gh release create "$TAG" --title "Aftergrid ${TAG#v}" --notes "Run AftergridUSBMaker.exe."
( cd "$OUT/parts" && sha256sum *.part > "$OUT/SHA256SUMS-parts.txt" )
cp "$(dirname "$0")/build/config/includes.chroot/usr/share/aftergrid/catalog.json" "$OUT/catalog.json"   # the packs USB Maker offers
gh release upload "$TAG" "$OUT"/parts/*.part "$OUT/latest.json" "$OUT/catalog.json" "$OUT/SHA256SUMS-parts.txt" "$OUT"/*.iso.sha256 --clobber
echo "Done. The USB Maker finds it at: https://github.com/$(gh repo view --json nameWithOwner -q .nameWithOwner)/releases/latest/download/latest.json"
echo "Point getaftergrid.com/releases/latest.json there with a redirect (vercel.json)."
