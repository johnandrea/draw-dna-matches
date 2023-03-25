@echo off

if exist run.out del run.out
if exist run.err del run.err
if exist adop-plus-birth-fam.dot del adop-plus-birth-fam.dot
if exist adop-plus-birth-fam.svg del adop-plus-birth-fam.svg
if exist adop-plus-birth-fam.png del adop-plus-birth-fam.png

draw-dna-matches.py --relation dnainfo adop-plus-birth-fam.ged >adop-plus-birth-fam.dot 2>run.err

set graphviz="c:\Program files\Graphviz\bin\dot.exe"

if exist %graphviz% (

   %graphviz% -Tpng adop-plus-birth-fam.dot -o adop-plus-birth-fam.png >>run.out 2>>run.err
   %graphviz% -Tsvg adop-plus-birth-fam.dot -o adop-plus-birth-fam.svg

) else (
  echo graphviz missing
)
