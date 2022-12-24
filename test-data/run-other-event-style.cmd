@echo off

if exist run.out del run.out
if exist run.err del run.err
if exist other-event-style.dot del other-event-style.dot
if exist other-event-style.png del other-event-style.png
if exist other-event-style.svg del other-event-style.svg

..\draw-dna-matches.py --relation --event=value dnainfo other-event-style.ged >other-event-style.dot 2>run.err

set graphviz="c:\Program files\Graphviz\bin\dot.exe"

if exist %graphviz% (

   %graphviz% -Tpng other-event-style.dot -o other-event-style.png >>run.out 2>>run.err
   %graphviz% -Tsvg other-event-style.dot -o other-event-style.svg

) else (
  echo graphviz missing
)
