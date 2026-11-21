#!/bin/bash
cd /home/claude/ark/marketing
for f in phone desk; do for c in home water food fallout tourniquet choking anaphylaxis heatstroke medtopic map langs askwater; do
  timeout 1500 node rec.js $f $c foot/$f/$c >> rec.log 2>&1 || echo "FAIL $f $c" >> rec.log; done; done
timeout 1500 node rec.js phone askbleed foot/phone/askbleed >> rec.log 2>&1 || echo "FAIL phone askbleed" >> rec.log
echo ALLDONE >> rec.log
