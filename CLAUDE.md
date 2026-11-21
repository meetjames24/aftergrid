# Aftergrid

Offline grid-down live Linux USB (Debian trixie, KDE Plasma). Formerly ARK / Cairn. Site: getaftergrid.com.

## Layout
- `build-aftergrid.sh <core|standard|full>` - builds the ISO (live-build), appends the library, splits into 380 MB parts in `out/parts/` with `aftergrid-image.json`. Needs root, ~20 GB free.
- `fetch-content.sh` - downloads ZIMs, models, maps, packages (all gitignored).
- `build/config/` - live-build config. Everything shipped in the OS is under `includes.chroot/`:
  - `usr/share/aftergrid/portal/` - Field Mode web app (index, ask.html = offline AI with citations, read.html, maps, search). Served by lighttpd :80.
  - `usr/local/bin/aftergrid-*` - setup wizard, AI server launcher, semantic search, control menu, low-power.
  - `etc/systemd/system/` - kiwix, llama-server (AI :8081), embeddings (:8082), semantic (:8083).
- `content/cards/` - 30 first-aid cards + 14 SVG diagrams (`cards.py`, `diagrams.py`). `content/tools/make_zims.py` builds them into ZIMs.
- `i18n/` - `langs.py` (EN, EL, FR, DE, PT, TR) -> `gen.py` -> `aftergrid-i18n.js`.
- `flasher/usbmaker/` - Windows USB Maker (C# WinForms). Build: `mcs` against `/usr/lib/mono/4.7-api` (not mono's own mscorlib; see git log).
- `eval/` - retrieval and answer tests (`score.js`, `answers.js`, `stack.sh`).
- `marketing/` - social kit generators.

## Rules
- Don't compile the ISO unless asked ("compile full").
- First-aid content needs clinical sign-off; never invent dosages or numbers.
- Live user is `aftergrid`; `user-setup` package must stay in the package list (live-config needs it to create the user).
