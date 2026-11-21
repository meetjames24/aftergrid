#!/bin/bash
cd /home/claude/ark/marketing
for x in "phone askwater" "desk askwater" "phone askbleed"; do set -- $x; timeout 1500 node rec.js $1 $2 foot/$1/$2 >> rec.log 2>&1 || echo "FAIL $x" >> rec.log; done
echo ASKDONE >> rec.log
