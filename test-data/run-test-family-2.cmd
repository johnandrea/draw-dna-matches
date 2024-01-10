@echo off

del run.out
del run.err
del test-family-2.dot
del test-family-2.png
del test-family-2.svg
del test-family-2-matrix.dot
del test-family-2-matrix.png
del test-family-2-matrix.svg

draw-dna-matches.py --relation dnamatch test-family-2.ged >test-family-2.dot 2>run.err
draw-dna-matches.py --format=matrix --relation dnamatch test-family-2.ged >test-family-2-matrix.dot 2>>run.err

set graphviz="c:\Program files\Graphviz\bin\dot.exe"

if exist %graphviz% (

   %graphviz% -Tpng test-family-2.dot -o test-family-2.png >run.out 2>>run.err
   %graphviz% -Tsvg test-family-2.dot -o test-family-2.svg
   %graphviz% -Tpng test-family-2-matrix.dot -o test-family-2-matrix.png >>run.out 2>>run.err
   %graphviz% -Tsvg test-family-2-matrix.dot -o test-family-2-matrix.svg

) else (
  echo graphviz missing
)
