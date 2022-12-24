@echo off

if exist run.out del run.out
if exist run.err del run.err
if exist bad-data.dot del bad-data.dot
if exist bad-data.png del bad-data.png
if exist bad-data.svg del bad-data.svg

draw-dna-matches.py --relation dnamatch bad-data.ged >bad-data.dot 2>run.err

set graphviz="c:\Program files\Graphviz\bin\dot.exe"

if exist %graphviz% (

   %graphviz% -Tpng bad-data.dot -o bad-data.png >>run.out 2>>run.err
   %graphviz% -Tsvg bad-data.dot -o bad-data.svg

) else (
  echo graphviz missing
)
