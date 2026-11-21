# Aftergrid 1.1: field guide

Aftergrid is a complete off-grid computer on a USB stick. It boots on almost any PC.
It works fully offline and brings these with it:
- an offline library (medical, water, food, shelter, repair)
- street maps
- a local AI that answers from the library
- mesh and radio messaging
- tools to share all of it to phones over Wi-Fi

## Start here: Field Mode
Open the **Aftergrid Field Mode** icon on the desktop, or go to http://localhost in any
browser. Big buttons: Medical · Water · Food · Shelter & Survival · Repair & Build ·
Power · Maps · Comms · Ask Aftergrid · Everything · Go-Bag. The search box searches
every book at once.

## Languages: English, Ελληνικά, Français, Deutsch, Português, Türkçe
- **Boot menu:** **Language...** lists all six. Each sets the desktop language and
  keyboard (Alt+Shift switches back to US English). Greek also has its own top-level entry.
- **Field Mode:** the language list at the top right switches every page. Map labels
  follow it.
- **Desktop:** Aftergrid Control, the welcome message, Firefox and LibreOffice
  (spell check included) follow the language you booted.
- **Ask Aftergrid:** ask in your language. It searches the library, which is mostly
  English, and answers in your language. The small AI is weaker outside English:
  tick **Answer in English** for medical or critical questions.
- **Library in your language:** Greek Wikipedia summaries ship inside Aftergrid. The
  others are downloads: `greek`, `french`, `german`, `portuguese` and `turkish`, and
  `med-intl` for medical Wikipedia in French, German and Portuguese (~0.6 GB).
- **Greek quick-start guide:** AFTERGRID-ODIGOS-EL.md.

## Share with phones (hotspot)
Go to Aftergrid Control → **Share the library over Wi-Fi**. Phones join the Wi-Fi
**Aftergrid-Library** (default password `aftergrid`, which you can change), and most
open the portal automatically. If one doesn't, open **http://10.42.0.1**.
- While the hotspot is on, this machine is not connected to other Wi-Fi.
- Some Wi-Fi chips can't be an access point. A cheap USB Wi-Fi adapter fixes that.

## Boot menu
| Entry | Use it when |
|---|---|
| **Encrypted persistence** (default) | Normal use. Asks for your passphrase and saves everything you change. |
| Fresh session | Borrowed or untrusted PC. Nothing is saved. |
| Load to RAM | Runs the system from memory so it is fast on slow sticks. Needs 16 GB+ RAM. Field Mode content may be unavailable in this mode. |
| Safe graphics | Black screen or garbled display. |
| Language... | Start in Greek, French, German, Portuguese or Turkish. |

To boot, use the PC's boot-menu key: F12 (Dell/Lenovo), F9 (HP), F8 (ASUS),
F11 (MSI), Esc on others. Aftergrid is Secure Boot signed.

**Macs:**
- Intel Macs: hold **Option** at power-on.
- 2018–2020 Macs with the T2 chip: first allow external boot in Startup Security
  Utility. The built-in keyboard, trackpad and Wi-Fi may not work, so use USB ones.
- Apple Silicon (M1 and later) can't boot Aftergrid directly. Run Aftergrid in a virtual
  machine instead (UTM), using the Aftergrid overlay.

## First-time setup (once per stick)
1. Boot **Fresh session**. Go to Aftergrid Control → **Set up this stick** and choose a
   passphrase. It creates:
   - **Persistence**: encrypted, holds settings, logins and files. 8 GB on sticks
     under 40 GB, 16 GB under 100 GB, 32 GB above that.
   - **VAULT**: the rest of the stick, exFAT. It holds extra downloads, and
     Windows and Mac can read it.
2. Reboot and choose **Encrypted persistence**.
3. Sign in to Claude and Chrome once. If KDE Wallet asks, create a wallet with a
   blank password; it's already on an encrypted partition.

On first start a short setup walks you through: language, encrypted saves on the stick, your own account (after one restart), Wi-Fi and downloads. Every step is optional. Run it again any time: Aftergrid Control → Run first-time setup again.

## What ships inside Aftergrid (no download needed)
- **Medical:** WikiMed (full medical encyclopedia), the medicine collection, US Army
  First Aid (FM 4-25.11), the Special Forces Medical Handbook (ST 31-91B), and
  Emergency War Surgery, plus the Aftergrid First Aid Cards.
- **Field manuals, searchable:** every page of the Army, survival and medical manuals is in the
  library search (book: Field Manuals), with a button to open that page of the original PDF.
- **Survival:**
  - post-disaster, water, food-preparation and knots collections
  - Army Survival (ATP 3-50.21 and FM 21-76)
  - Field Hygiene and Sanitation (FM 21-10)
  - Nuclear War Survival Skills
- **Build and repair:** Appropedia (appropriate technology, solar, water, farming).
- **Greek:** Greek Wikipedia, with a summary of every article.
- **Maps:** a world overview, Greece, detailed Crete, and detailed Arkansas.
- **Offline AI:** Qwen3 4B (full edition only).

## Get more (Aftergrid Control → Download)
| Tier | What |
|---|---|
| core | iFixit repair guides (WikiMed and the packs only download if your edition lacks them) |
| med | Wikipedia Medicine, plus LibreTexts medicine, biology and chemistry |
| skills | Stack Exchange (outdoors, DIY, gardening, cooking, ham radio, electronics), Wikibooks, Wikivoyage |
| ai / ai-large | Offline AI models: Qwen3 4B (8 GB RAM) or Bonsai 27B (16 GB RAM) |
| maps-europe / maps-usa | Street-level maps of Europe or the US |
| wikipedia / books | All of Wikipedia; Project Gutenberg |
| greek / french / german / portuguese / turkish | Wikipedia in that language (plus medical Wikipedia or Wiktionary) |
| med-intl | Medical Wikipedia in French, German and Portuguese |

**No internet?** Aftergrid Control → **Copy library from another Aftergrid stick**. It copies
everything you don't have from a friend's VAULT.

## Ask Aftergrid (offline AI)
Go to Field Mode → **Ask Aftergrid** and ask in plain words ("my kid swallowed something and can't breathe").
- **How it finds answers:** it searches the whole library by keywords, by the article titles it expects
  to answer you, and by meaning (for the first-aid cards and field manuals). It reads the best three
  sources and answers only from them.
- **First-aid cards come first** for medical questions: 30 short protocols (bleeding, CPR, choking,
  allergic reactions, burns, cold, heat, poisoning, childbirth and more), each naming the guideline it follows.
- **Tap any [1] [2] [3]** in an answer to open that source with the exact passage highlighted.
- **Numbers are checked:** if the answer contains a number its sources don't, a warning names it.
- **Which AI model:** the biggest one your PC can run well. Qwen3 4B (8 GB RAM) ships inside; Qwen3 8B
  (14 GB+ RAM) is the `ai-8b` download and is used automatically when present.
- It starts by itself on PCs with 12 GB+ RAM. Otherwise: Aftergrid Control → Start / stop the offline AI.
- An answer takes about 1 to 2 minutes on a laptop CPU, faster with a graphics card.
- Always open the source for anything critical, such as doses or procedures.

## Day and Night
Field Mode is light by default. **Night** (top right) switches every page and the map to dark, which is
easier in a dark room and saves battery on phone screens. Low power mode switches to Night by itself.

## Comms (Field Mode → Comms has the frequency card; print it)
- **Mesh messenger** (Reticulum/NomadNet): encrypted messages between Aftergrid
  machines on the same Wi-Fi or hotspot, or over LoRa radios. No internet needed.
- **Meshtastic** (`meshtastic` in a terminal): LoRa mesh radios.
- **CHIRP**: program handheld radios. **JS8Call / fldigi**: HF keyboard messaging.
  **Pat**: Winlink email over radio. **Direwolf**: APRS and packet radio.
- **SDR** (cheap USB RTL-SDR dongle): Gqrx to listen, rtl_433 for sensors,
  Gpredict for satellites.
- A licence is needed to transmit on ham bands. Listening is always fine.

## Power
Aftergrid Control → **Low power mode** switches on the power-saver profile, dims the
screen, turns Bluetooth off and enables device power-saving.

## Go-Bag
- **Field Mode → Go-Bag:** fill in and print an emergency card for each person.
- **GoBag folder** in your home folder: scans of IDs, prescriptions and insurance.
  It's on the encrypted part of the stick.

## Install to a hard drive
Aftergrid Control → **Install Aftergrid onto this computer's disk**. Choose **Manual
partitioning** and set up three things:
- **Your empty partition:** format it as ext4, mount point `/`.
- **The EFI partition:** mount point `/boot/efi`, **don't format it**.
- **Everything else, including Windows:** leave alone.

The installer copies the offline library onto the disk too.

## Raspberry Pi and other Linux machines
`/run/live/medium/aftergrid-library/overlay/` holds the Aftergrid overlay. Run
`sudo ./aftergrid-overlay-install.sh aftergrid-overlay.tar.gz` on Debian 13 or Raspberry Pi
OS (64-bit), with internet once, to turn that machine into Aftergrid. Then copy the
`aftergrid-library` folder to `/opt/aftergrid-library`.

## Rebuild or replace the stick
Flash the Aftergrid ISO with the Aftergrid flasher, or with Rufus in **DD mode**, then run
**Set up this stick** again. Flashing a new version wipes the stick, so copy
anything you want from VAULT and from your home folder first.

## Licences
- Maps: © OpenStreetMap contributors (ODbL), Protomaps.
- WikiMed, Appropedia and Wikipedia-family content: CC BY-SA.
- US Army manuals: US government works.
- Qwen3: Apache 2.0.
- iFixit: CC BY-NC-SA. It's a download tier, not baked in, because it can't be
  redistributed commercially.
- The zimgit collections bundle documents from many publishers; check each one
  before redistributing Aftergrid commercially.
