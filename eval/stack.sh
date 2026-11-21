#!/bin/bash
# Bring up the Aftergrid test stack: web server, library server, offline AI (+ embeddings and semantic search when present).
cd /tmp
pgrep -f "kiwix-serve.*8080" >/dev/null || (setsid nohup kiwix-serve --library --monitorLibrary --address=127.0.0.1 --port=8080 --urlRootLocation=/kiwix /run/aftergrid/library.xml >/tmp/kiwix.log 2>&1 &)
pgrep -x lighttpd >/dev/null || (setsid nohup lighttpd -D -f /tmp/a.conf >/tmp/lt.log 2>&1 &)
pgrep -f "llama-server.*8081" >/dev/null || (setsid nohup /opt/llama/bin/llama-server -m /home/claude/ark/content/models/qwen3-4b/Qwen3-4B-Instruct-2507-Q4_K_M.gguf --host 127.0.0.1 --port 8081 -c 4096 -np 1 -fa on -ctk q8_0 -ctv q8_0 -ngl 0 --jinja --no-webui >/tmp/llama.log 2>&1 &)
E=/home/claude/ark/content/models/embed/bge-small-en-v1.5-q8_0.gguf
[ -f "$E" ] && ! pgrep -f "llama-server.*8082" >/dev/null && (setsid nohup /opt/llama/bin/llama-server -m $E --host 127.0.0.1 --port 8082 --embedding --pooling cls -c 2048 -ub 512 -b 2048 --no-webui >/tmp/embed.log 2>&1 &)
S=/home/claude/ark/build/config/includes.chroot/usr/local/bin/aftergrid-semantic
[ -x "$S" ] && ! pgrep -f aftergrid-semantic >/dev/null && (AFTERGRID_INDEX=/home/claude/ark/content/ai/semantic setsid nohup python3 $S >/tmp/sem.log 2>&1 &)
for i in $(seq 1 60); do curl -s localhost:8081/health | grep -q ok && break; sleep 2; done
for u in localhost/ localhost:8080/kiwix/ localhost:8081/health localhost:8082/health localhost:8083/health; do printf "%s %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' $u)"; done
