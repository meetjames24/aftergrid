#!/bin/bash
# Aftergrid overlay installer: turn an existing Debian 13 / Raspberry Pi OS (trixie) system,
# x86_64 or arm64 (Raspberry Pi 4/5, ARM laptops, VMs on Apple Silicon), into Aftergrid.
#
#   sudo ./aftergrid-overlay-install.sh /path/to/aftergrid-overlay.tar.gz
#
# Needs internet once (apt). Installs Aftergrid's portal, library server, tools and services.
# The offline library itself: copy an Aftergrid stick's aftergrid-library folder to /opt/aftergrid-library,
# or run aftergrid-vault-sync --dest /opt/aftergrid-library core.
set -euo pipefail
[ "$(id -u)" = 0 ] || exec sudo "$0" "$@"
TAR="${1:-$(dirname "$0")/aftergrid-overlay.tar.gz}"
[ -f "$TAR" ] || { echo "usage: $0 aftergrid-overlay.tar.gz"; exit 1; }
ARCH=$(dpkg --print-architecture)
echo "Installing Aftergrid overlay on $ARCH ($(. /etc/os-release; echo $PRETTY_NAME))"

PKGS="lighttpd kiwix-tools python3-venv python3-pip network-manager dnsmasq-base kdialog konsole
      keepassxc syncthing chirp fldigi js8call direwolf gqrx-sdr rtl-sdr rtl-433 gpredict
      powertop brightnessctl exfatprogs cryptsetup aria2 curl jq rsync okular vulkan-tools"
apt-get update
apt-get install -y --no-install-recommends $PKGS || apt-get install -y --no-install-recommends $(for p in $PKGS; do apt-cache show $p >/dev/null 2>&1 && echo $p; done)

# Claude (desktop app supports amd64 + arm64; Claude Code CLI too)
install -d /usr/share/keyrings /etc/apt/keyrings
curl -fsSL https://downloads.claude.ai/claude-desktop/key.asc -o /usr/share/keyrings/claude-desktop-archive-keyring.asc || true
curl -fsSL https://downloads.claude.ai/keys/claude-code.asc -o /etc/apt/keyrings/claude-code.asc || true
echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/claude-desktop-archive-keyring.asc] https://downloads.claude.ai/claude-desktop/apt/stable stable main" > /etc/apt/sources.list.d/claude-desktop.list
echo "deb [signed-by=/etc/apt/keyrings/claude-code.asc] https://downloads.claude.ai/claude-code/apt/stable stable main" > /etc/apt/sources.list.d/claude-code.list
apt-get update && apt-get install -y claude-code || true
apt-get install -y claude-desktop || echo "(Claude desktop app not available for this system; use claude.ai in the browser)"

# Aftergrid files (portal, scripts, units, skeleton). Binaries built for x86_64 are skipped on arm64.
tar -xzf "$TAR" -C / --exclude='./opt/llama' --exclude='./usr/local/bin/pat' --exclude='./usr/local/bin/pmtiles'
if [ "$ARCH" = amd64 ]; then tar -xzf "$TAR" -C / ./opt/llama ./usr/local/bin/pat ./usr/local/bin/pmtiles 2>/dev/null || true; fi

# Python tools: library MCP, Meshtastic, Reticulum/NomadNet
python3 -m venv /opt/aftergrid/venv
/opt/aftergrid/venv/bin/pip install -q openzim-mcp meshtastic rns lxmf nomadnet
ln -sf /opt/aftergrid/venv/bin/openzim-mcp /usr/local/bin/openzim-mcp
for b in meshtastic rnsd rnstatus rnpath rnprobe nomadnet lxmd; do ln -sf /opt/aftergrid/venv/bin/$b /usr/local/bin/$b; done

# arm64: build the map tool, Pat and llama.cpp from source if Go / a compiler are available
if [ "$ARCH" != amd64 ]; then
  apt-get install -y golang-go cmake g++ git libvulkan-dev glslc spirv-headers || true
  GOBIN=/usr/local/bin go install github.com/protomaps/go-pmtiles@latest && mv /usr/local/bin/go-pmtiles /usr/local/bin/pmtiles || true
  GOBIN=/usr/local/bin CGO_ENABLED=0 go install github.com/la5nta/pat@latest || true
  if [ ! -x /opt/llama/bin/llama-server ]; then
    tmp=$(mktemp -d); git clone --depth 1 https://github.com/ggml-org/llama.cpp "$tmp/l" && \
    cmake -S "$tmp/l" -B "$tmp/b" -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF -DCMAKE_INSTALL_PREFIX=/opt/llama && \
    cmake --build "$tmp/b" -j"$(nproc)" --target llama-server && cmake --install "$tmp/b" || echo "(llama.cpp build failed: offline AI unavailable)"
  fi
fi
printf "/opt/llama/bin\n/opt/llama/lib\n" > /etc/ld.so.conf.d/aftergrid-llama.conf; ldconfig
mkdir -p /var/log/lighttpd && chown www-data:www-data /var/log/lighttpd
mkdir -p /opt/aftergrid-library/{zim,maps,library,models}
systemctl daemon-reload
systemctl enable --now aftergrid-refresh.service aftergrid-refresh.path aftergrid-kiwix.service lighttpd.service || true
systemctl enable aftergrid-ai.service || true
systemctl restart NetworkManager || true
echo
echo "Aftergrid overlay installed. Open http://localhost/ (Field Mode)."
echo "Add the library: copy aftergrid-library/ from an Aftergrid stick to /opt/aftergrid-library, or: aftergrid-vault-sync --dest /opt/aftergrid-library core"
