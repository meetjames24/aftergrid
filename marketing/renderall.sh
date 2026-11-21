#!/bin/bash
cd /home/claude/ark/marketing
for v in reel-02-medical-emergency reel-01-grid-down reel-03-every-phone landscape-01-aftergrid-demo; do
  python3 kit.py $v >> render.log 2>&1 || echo "FAIL $v" >> render.log; done
echo RENDERDONE >> render.log
