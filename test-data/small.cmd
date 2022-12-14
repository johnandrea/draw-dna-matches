@echo off

if exist run.out del run.out
if exist run.err del run.err
if exist small.dot del small.dot
if exist small.png del small.png
if exist small.svg del small.svg

draw-dna-matches.py --relation dnamatch small.ged >small.dot 2>run.err

set graphviz="c:\Program files\Graphviz\bin\dot.exe"

if exist %graphviz% (

   %graphviz% -Tpng small.dot -o small.png >>run.out 2>>run.err
   %graphviz% -Tsvg small.dot -o small.svg

) else (
  echo graphviz missing
)
