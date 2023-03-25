@echo off

if exist run.out del run.out
if exist run.err del run.err
if exist adop.dot del adop.dot
if exist adop.svg del adop.svg
if exist adop.png del adop.png

draw-dna-matches.py --relation dnainfo adop.ged >adop.dot 2>run.err

set graphviz="c:\Program files\Graphviz\bin\dot.exe"

if exist %graphviz% (

   %graphviz% -Tpng adop.dot -o adop.png >>run.out 2>>run.err
   %graphviz% -Tsvg adop.dot -o adop.svg

) else (
  echo graphviz missing
)
