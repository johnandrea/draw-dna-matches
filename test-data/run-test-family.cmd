@echo off

del run.out
del run.err
del test-family.dot
del test-family.png
del test-family.svg
del test-family-matrix.dot
del test-family-matrix.png
del test-family-matrix.svg

draw-dna-matches.py --relation dnamatch test-family.ged >test-family.dot 2>run.err
draw-dna-matches.py --format=matrix --relation dnamatch test-family.ged >test-family-matrix.dot 2>>run.err

set graphviz="c:\Program files\Graphviz\bin\dot.exe"

if exist %graphviz% (

   %graphviz% -Tpng test-family.dot -o test-family.png >run.out 2>>run.err
   %graphviz% -Tsvg test-family.dot -o test-family.svg
   %graphviz% -Tpng test-family-matrix.dot -o test-family-matrix.png >>run.out 2>>run.err
   %graphviz% -Tsvg test-family-matrix.dot -o test-family-matrix.svg

) else (
  echo graphviz missing
)
