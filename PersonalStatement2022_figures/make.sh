pdflatex feynman
for f in `ls *.mp`; do mpost $f; done
pdflatex feynman
../cpdf-binaries/OSX-Intel/cpdf feynman.pdf 1 -o feynman1.pdf
../cpdf-binaries/OSX-Intel/cpdf feynman.pdf 2 -o feynman2.pdf
