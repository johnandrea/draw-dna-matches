@echo off

if exist run.out del run.out
if exist run.err del run.err
if exist double-cousins-plus.dot del double-cousins-plus.dot
if exist double-cousins-plus.png del double-cousins-plus.png
if exist double-cousins-plus.svg del double-cousins-plus.svg

draw-dna-matches.py --relation dnamatch double-cousins-plus.ged >double-cousins-plus.dot 2>run.err

set graphviz="c:\Program files\Graphviz\bin\dot.exe"

if exist %graphviz% (

   %graphviz% -Tpng double-cousins-plus.dot -o double-cousins-plus.png >>run.out 2>>run.err
   %graphviz% -Tsvg double-cousins-plus.dot -o double-cousins-plus.svg

) else (
  echo graphviz missing
)
