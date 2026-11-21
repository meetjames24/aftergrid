#!/bin/bash
cd /home/claude/ark/eval
node score.js final4 > final4.log 2>&1
node answers.js final3 > answers.log 2>&1
echo ALLDONE >> answers.log
