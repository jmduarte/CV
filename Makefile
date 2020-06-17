tex: cv_duarte_javier

cv_duarte_javier:
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier
	biber cv_duarte_javier
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier

lint:
	grep -E --color=always -r -i --include=\*.tex --include=\*.bib "(\b[a-zA-Z]+) \1\b" || true

clean:
	rm -f *.aux *.bbl *.blg *.dvi *.idx *.lof *.log *.lot *.toc \
	*.xdy *.nav *.out *.snm *.vrb *.mp \
	*.synctex.gz *.brf *.fls *.fdb_latexmk \
	*.glg *.gls *.glo *.ist *.alg *.acr *.acn *.bcf *.xml
	find . -type f -name '*.aux' -delete

realclean: clean
	rm -f cv_duarte_javier*.ps cv_duarte_javier*.pdf
