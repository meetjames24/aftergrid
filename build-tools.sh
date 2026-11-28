#!/bin/bash
# Build the binaries Aftergrid ships that Debian 13 doesn't package, inside a clean Debian 13
# (trixie) chroot so they match the OS exactly. No GitHub downloads needed:
#   /opt/llama            ggml + llama.cpp (llama-server), CPU (all x86-64 variants) + Vulkan GPU,
#                         from the source tarballs in Debian's own archive
#   usr/local/bin/pmtiles go-pmtiles   (map extracts)      via the Go module proxy
#   usr/local/bin/pat     Pat Winlink client              via the Go module proxy
# Needs root, debootstrap, ~3 GB. Output goes into build/config/includes.chroot.
#   sudo ./build-tools.sh            (re-running skips what's already built)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
INC="$HERE/build/config/includes.chroot"; CH="$HERE/work/tools-chroot"
MIRROR=http://deb.debian.org/debian
GGML=ggml_1.1.1.orig.tar.gz;                 GGML_SHA=24097461b3021a628c4dd31a21a78b9f2483e0ee671e44a6c29629b777132450
LLAMA=llama.cpp_1.1.0+dfsg.orig.tar.xz;     LLAMA_SHA=87cb77fd756841d039532370ff466dba10261c6968fccc00f2a8f037ee42c90e
[ "$(id -u)" = 0 ] || exec sudo "$0" "$@"

if [ ! -x "$CH/usr/bin/cmake" ]; then
  echo "== Debian 13 build chroot"
  mkdir -p "$CH"; debootstrap --variant=minbase trixie "$CH" "$MIRROR" >/dev/null
  cp /etc/resolv.conf "$CH/etc/resolv.conf" 2>/dev/null || true
fi
mnt(){ for d in proc sys dev; do mountpoint -q "$CH/$d" || mount --bind /$d "$CH/$d"; done; }
umnt(){ for d in dev sys proc; do umount -l "$CH/$d" 2>/dev/null || true; done; }
trap umnt EXIT; mnt
# pass the host's proxy settings and CA bundle through (CI / proxied networks)
for v in http_proxy https_proxy HTTP_PROXY HTTPS_PROXY no_proxy NO_PROXY; do [ -n "${!v:-}" ] && export "$v"; done
if [ -n "${SSL_CERT_FILE:-}" ] && [ -f "$SSL_CERT_FILE" ]; then cp "$SSL_CERT_FILE" "$CH/host-ca.crt"; fi
run(){ chroot "$CH" /usr/bin/env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root \
       http_proxy="${http_proxy:-}" https_proxy="${https_proxy:-}" HTTPS_PROXY="${HTTPS_PROXY:-}" HTTP_PROXY="${HTTP_PROXY:-}" \
       SSL_CERT_FILE="$( [ -f "$CH/host-ca.crt" ] && echo /host-ca.crt )" GIT_SSL_CAINFO="$( [ -f "$CH/host-ca.crt" ] && echo /host-ca.crt )" \
       DEBIAN_FRONTEND=noninteractive /bin/bash -euo pipefail -c "$1"; }
run "[ -x /usr/bin/cmake ] || { apt-get update -q && apt-get install -y -q --no-install-recommends build-essential cmake pkg-config \
      ca-certificates curl xz-utils libvulkan-dev glslc spirv-headers golang-go git >/dev/null; }"

if [ ! -x "$INC/opt/llama/bin/llama-server" ]; then
  echo "== ggml + llama.cpp (Debian source, CPU variants + Vulkan)"
  run "set -x; mkdir -p /src && cd /src
    get(){ [ -f \$1 ] || curl -fsSL -o \$1 $MIRROR/pool/main/\$2/\$1; echo \"\$3  \$1\" | sha256sum -c -; }
    get $GGML g/ggml $GGML_SHA; get $LLAMA l/llama.cpp $LLAMA_SHA
    rm -rf ggml llama && mkdir ggml llama && tar -xzf $GGML -C ggml --strip-components=1 && tar -xJf $LLAMA -C llama --strip-components=1
    R=(-DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/llama -DCMAKE_INSTALL_RPATH=/opt/llama/lib -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON)
    # GGML_NATIVE=OFF + all CPU variants: runs on any x86-64 PC, picks the fastest code for each CPU at start
    cmake -S ggml -B ggml/b \"\${R[@]}\" -DGGML_NATIVE=OFF -DGGML_BACKEND_DL=ON -DGGML_CPU_ALL_VARIANTS=ON -DGGML_VULKAN=ON \
          -DGGML_BUILD_TESTS=OFF -DGGML_BUILD_EXAMPLES=OFF >/dev/null
    cmake --build ggml/b -j\$(nproc) >/dev/null && cmake --install ggml/b >/dev/null
    cmake -S llama -B llama/b \"\${R[@]}\" -DLLAMA_USE_SYSTEM_GGML=ON -DCMAKE_PREFIX_PATH=/opt/llama -DLLAMA_CURL=OFF \
          -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=ON >/dev/null
    cmake --build llama/b -j\$(nproc) --target llama-server >/dev/null
    install -Dm755 llama/b/bin/llama-server /opt/llama/bin/llama-server
    cp -a llama/b/bin/*.so* /opt/llama/lib/ 2>/dev/null || true; find llama/b -name 'libllama*.so*' -exec cp -a {} /opt/llama/lib/ \\;
    /opt/llama/bin/llama-server --version"
  mkdir -p "$INC/opt"; rm -rf "$INC/opt/llama"; cp -a "$CH/opt/llama" "$INC/opt/llama"
else echo "== llama.cpp: already built"; fi

for t in pmtiles:github.com/protomaps/go-pmtiles pat:github.com/la5nta/pat; do
  n=${t%%:*}; m=${t#*:}
  if [ ! -x "$INC/usr/local/bin/$n" ]; then
    echo "== $n ($m)"
    run "export GOPATH=/root/go GOTOOLCHAIN=auto CGO_ENABLED=0; go install $m@latest >/dev/null; ls /root/go/bin"
    b=$(basename "$m"); install -Dm755 "$CH/root/go/bin/$b" "$INC/usr/local/bin/$n"
  else echo "== $n: already built"; fi
done
"$INC/usr/local/bin/pmtiles" version 2>/dev/null | head -1 || true
echo "Done: $(du -sh "$INC/opt/llama" | cut -f1) llama.cpp, pmtiles, pat in $INC"
