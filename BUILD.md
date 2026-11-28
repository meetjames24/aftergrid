# Building Aftergrid

```
sudo ./fetch-content.sh            # once: tools (build-tools.sh) + library, ~7 GB
sudo ./build-aftergrid.sh standard # or: full | lite   (SPLIT=0 for a single .iso, REUSE_BASE=1 to re-stage only)
```
CI: pushing a `v*` tag runs `.github/workflows/iso.yml` (ISO -> release) and `release.yml` (signed USB Maker -> release).

Output: `out/parts/Aftergrid-1.1-<profile>.iso.NN.part` + `FLASH-Aftergrid.bat` / `flash-aftergrid.ps1` / `LIST-USB.bat`
(Windows: put all in one folder, double-click FLASH-Aftergrid.bat) and `out/Aftergrid-1.1-<profile>.iso.sha256`.

## Layout
| Path | What |
|---|---|
| `build/config/` | live-build config: packages, boot menu, hooks, `includes.chroot/` (everything Aftergrid adds) |
| `content/` | offline library baked into the ISO at `/aftergrid-library` (zim/, maps/, library/, models/) |
| `flasher/` | Windows join-verify-flash script template |
| `build-aftergrid.sh` | base build → stage profile → add library → split |

## Moving parts inside Aftergrid
- `lighttpd` :80 serves the Field Mode portal (`/usr/share/aftergrid/portal`), proxies `/kiwix` → kiwix-serve :8080 and `/ai/` → llama-server :8081. Only localhost and hotspot clients (10.42.x.x) are answered.
- `aftergrid-refresh` (service + path unit + udev on VAULT) rebuilds `/run/aftergrid/library.xml` and `/run/aftergrid/index.json` from `/run/live/medium/aftergrid-library`, `/opt/aftergrid-library` (installed systems), `/vault`.
- `aftergrid-kiwix` serves the library (monitors library.xml). `aftergrid-ai` runs llama.cpp when a model exists (baked in, or in the VAULT) and RAM ≥ 6 GB, or `/run/aftergrid/ai-force` is set. `aftergrid-ai-doctor` explains why it isn't running.
- `aftergrid-hotspot` = NetworkManager shared AP + dnsmasq catch-all DNS (captive portal).
- Installer (Calamares) runs `shellprocess@aftergrid` to copy the library to `/opt/aftergrid-library`.

## Updating content
- Maps: `pmtiles extract https://build.protomaps.com/<YYYYMMDD>.pmtiles content/maps/<name>.pmtiles --bbox=W,S,E,N --maxzoom=N`
- ZIMs: newest from download.kiwix.org (verify the .sha256).

## ARM64 (Raspberry Pi 4/5, ARM laptops, UTM on Apple Silicon)
- Easiest: Debian 13 / Raspberry Pi OS 64-bit + `aftergrid-library/overlay/aftergrid-overlay-install.sh` (needs internet once; builds pmtiles, Pat and llama.cpp from source on the device).
- Native arm64 live ISO (untested): on an arm64 Debian host run `lb config --architecture arm64 --bootloaders grub-efi` with the same config; drop `google-chrome-stable`, `intel-microcode`, `amd64-microcode` and the amd64 binaries (`/opt/llama`, `pat`, `pmtiles`) and rebuild those for arm64.
