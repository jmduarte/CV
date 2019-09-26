#!/bin/bash -e                                                                                                                                       
ECHO="echo -e"

run_pdflatex(){
pdflatex -interaction=nonstopmode -synctex=-1 "$1.tex" > "$1.log" 2>&1
}

SOURCE=cv_duarte_javier
$ECHO "First pass\n"
run_pdflatex $SOURCE
$ECHO "bibtex"
biber "$SOURCE.aux"
$ECHO "\nSecond pass\n"
run_pdflatex $SOURCE
$ECHO "Third pass\n"
run_pdflatex $SOURCE
$ECHO "Done"