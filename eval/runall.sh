#!/bin/bash
cd $(git -C "$(dirname "$0")" rev-parse --show-toplevel)/eval
node score.js final4 > final4.log 2>&1
node answers.js final3 > answers.log 2>&1
echo ALLDONE >> answers.log
