<p align="center"><img src="docs/logo.png" alt="Aftergrid" width="360"></p>

<p align="center"><b>When the grid goes down, Aftergrid boots up.</b><br>
A complete offline survival and medical library, maps and a local AI on one USB stick. Plug it into any PC, boot, and it works with no internet.</p>

---

## What's on the stick

| | |
|---|---|
| **Field Mode** | One home screen for everything: Medical, Water, Food, Shelter, Repair, Power, Maps, Comms, Ask, Go-Bag. Works on the PC, and on any phone on the same Wi-Fi. |
| **Offline library** | 10 libraries and 7 field manuals: WikiMed medical encyclopedia, US Army First Aid (FM 4-25.11), Special Forces Medical Handbook (ST 31-91B), Emergency War Surgery, Appropedia, Greek Wikipedia and more. One search box covers all of them. |
| **First-aid cards** | 30 short cards for emergencies (bleeding, CPR, choking, burns, stroke, hypothermia, snake bite, childbirth…) with 14 drawn diagrams. Each card lists its sources. |
| **Ask Aftergrid** | A local AI (Qwen3, runs on the CPU, no internet) that answers from the library only, cites its sources, shows the relevant diagrams, and flags any number that isn't in the sources. |
| **Source links** | Every citation opens the original page with the exact passage highlighted. |
| **Offline maps** | Street-level vector maps that work offline, with "where am I". |
| **Comms** | Emergency and calling frequencies (marine, aviation, CB, PMR446, FRS/GMRS, ham, NOAA) and what you may legally do with each. |
| **Go-Bag card** | A printable emergency card for each family member, saved only on the encrypted stick. |
| **Encrypted saves** | Your files, notes and settings stay on the stick, encrypted (LUKS2). Lose the stick, nobody reads it. |
| **Six languages** | English, Ελληνικά, Français, Deutsch, Português, Türkçe: OS, portal and search. |
| **Day / Night** | Light by default, Night mode for the dark, and a low-power mode to save battery. |
| **Claude built in** | Claude desktop and Claude Code are preinstalled for when there *is* a connection. |
| **Setup wizard** | First boot walks you through language, encrypted saves, your own account, Wi-Fi (optional) and extra downloads. |
| **USB Maker for Windows** | One small program writes the stick and checks every byte afterwards. |

## Screenshots

### Field Mode
| Day | Night | Ελληνικά |
|---|---|---|
| ![Home, day](docs/screenshots/01-home-day.png) | ![Home, night](docs/screenshots/02-home-night.png) | ![Home in Greek](docs/screenshots/03-home-greek.png) |

### Medical and first aid
| Medical shelf | First-aid card | Diagrams |
|---|---|---|
| ![Medical topic](docs/screenshots/04-topic-medical.png) | ![Severe bleeding card](docs/screenshots/12-first-aid-card.png) | ![First-aid diagrams](docs/screenshots/15-first-aid-diagrams.jpg) |

### Ask Aftergrid (offline AI)
| Ask | Answer with sources and diagrams | Source, passage highlighted |
|---|---|---|
| ![Ask](docs/screenshots/09-ask-empty.png) | ![Answer with diagrams](docs/screenshots/13-ask-answer-with-diagrams.jpg) | ![Highlighted source](docs/screenshots/14-source-highlighted.png) |

### Search, maps, comms, go-bag
| Search the whole library | Offline maps |
|---|---|
| ![Search](docs/screenshots/05-search.png) | ![Maps](docs/screenshots/06-maps.png) |

| Radio frequencies | Emergency card |
|---|---|
| ![Comms](docs/screenshots/07-comms-radio.png) | ![Go-bag card](docs/screenshots/08-gobag-card.png) |

### On a phone
| Home | Search |
|---|---|
| <img src="docs/screenshots/10-phone-home.png" width="300"> | <img src="docs/screenshots/11-phone-search.png" width="300"> |

### Booting and setup
| Boot menu | Desktop + setup wizard | Wizard |
|---|---|---|
| ![Boot menu](docs/screenshots/16-boot-menu.png) | ![Desktop](docs/screenshots/17-desktop-setup-wizard.png) | ![Wizard](docs/screenshots/18-setup-wizard-welcome.png) |

### Making the stick on Windows
![USB Maker](docs/screenshots/19-usb-maker-windows.png)

## Build it

Needs Debian/Ubuntu, root, ~20 GB free disk.

```
./fetch-content.sh            # libraries, models, maps, packages (~9 GB, not in git)
sudo ./build-aftergrid.sh full   # or: core | standard
```

Output: `out/parts/` (the image in 380 MB parts + `aftergrid-image.json` + `Aftergrid USB Maker.exe`). Put the parts next to the USB Maker on Windows and run it, or on Linux/Mac: `cat Aftergrid-*.part | sudo dd of=/dev/sdX bs=4M`.

See `BUILD.md` for details and `CLAUDE.md` for the code map.

## Medical disclaimer

Aftergrid is reference material, not a substitute for trained help. First-aid cards are under clinical review; see the review checklist before relying on them.
