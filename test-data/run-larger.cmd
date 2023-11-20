@echo off

if exist run.out del run.out
if exist run.err del run.err
if exist larger.dot del larger.dot
if exist larger.png del larger.png
if exist larger.svg del larger.svg
if exist larger-matrix.dot del larger-matrix.dot
if exist larger-matrix.png del larger-matrix.png
if exist larger-matrix.svg del larger-matrix.svg

draw-dna-matches.py --relation dnamatch larger.ged >larger.dot 2>run.err
draw-dna-matches.py --format=matrix --title="DNA Matches in Family Tree" dnamatch larger.ged >larger-matrix.dot 2>run.err

set graphviz="c:\Program files\Graphviz\bin\dot.exe"

if exist %graphviz% (

   %graphviz% -Tpng larger.dot -o larger.png >>run.out 2>>run.err
   %graphviz% -Tsvg larger.dot -o larger.svg
   %graphviz% -Tpng larger-matrix.dot -o larger-matrix.png >>run.out 2>>run.err
   %graphviz% -Tsvg larger-matrix.dot -o larger-matrix.svg

) else (
  echo graphviz missing
)
