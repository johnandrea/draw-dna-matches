@echo off

if exist run.out del run.out
if exist run.err del run.err
if exist double-cousins.dot del double-cousins.dot
if exist double-cousins.png del double-cousins.png
if exist double-cousins.svg del double-cousins.svg

draw-dna-matches.py --relation dnamatch double-cousins.ged >double-cousins.dot 2>run.err

set graphviz="c:\Program files\Graphviz\bin\dot.exe"

if exist %graphviz% (

   %graphviz% -Tpng double-cousins.dot -o double-cousins.png >>run.out 2>>run.err
   %graphviz% -Tsvg double-cousins.dot -o double-cousins.svg

) else (
  echo graphviz missing
)
