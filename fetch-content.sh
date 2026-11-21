#!/bin/bash
cd /home/claude/ark/content
K=https://download.kiwix.org/zim
get(){ curl -fsSL --retry 5 -C - -o "$2" "$1" && echo "OK $2" || echo "FAIL $2"; }
for f in other/zimgit-water_en_2024-08.zim other/zimgit-medicine_en_2024-08.zim other/zimgit-food-preparation_en_2025-04.zim other/zimgit-knots_en_2024-08.zim other/zimgit-post-disaster_en_2024-05.zim other/appropedia_en_all_maxi_2026-02.zim other/mdwiki_en_all_maxi_2025-11.zim; do
  n=$(basename $f); get $K/$f zim/$n
  want=$(curl -fsSL $K/$f.sha256 | awk '{print $1}'); have=$(sha256sum zim/$n | awk '{print $1}'); [ "$want" = "$have" ] && echo "SHA OK $n" || echo "SHA BAD $n"
done
A=https://archive.org/download
get "$A/survival-atp-3-50-21/Survival%20%28ATP%203-50-21%29.pdf" manuals/survival/US-Army-ATP-3-50.21-Survival.pdf
get "$A/Fm21-76SurvivalManual/FM21-76_SurvivalManual.pdf" manuals/survival/US-Army-FM-21-76-Survival.pdf
get "$A/FM21-10_2000/FM21-10_2000.pdf" manuals/survival/US-Army-FM-21-10-Field-Hygiene-and-Sanitation.pdf
get "$A/FM4-25.11/FM4-25.11.pdf" manuals/medical/US-Army-FM-4-25.11-First-Aid.pdf
get "$A/ST_31-91B_Special_Forces_Medical_Handbook/ST_31-91B_Special_Forces_Medical_Handbook.pdf" manuals/medical/ST-31-91B-Special-Forces-Medical-Handbook.pdf
get "$A/ews5man-mil/ews5man.pdf" manuals/medical/Emergency-War-Surgery-5th-Ed.pdf
get "$A/NuclearWarSurvivalSkills_201311/Nuclear%20War%20Survival%20Skills.pdf" manuals/survival/Nuclear-War-Survival-Skills-Kearny.pdf
echo ALLDONE
