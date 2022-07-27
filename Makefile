tex: cv_duarte_javier publist_biobib

cv_duarte_javier:
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier
	biber cv_duarte_javier
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier

publist_biobib:
	pdflatex -interaction=nonstopmode -synctex=-1 publist_biobib
	biber publist_biobib
	pdflatex -interaction=nonstopmode -synctex=-1 publist_biobib
	pdflatex -interaction=nonstopmode -synctex=-1 publist_biobib
	pdflatex -interaction=nonstopmode -synctex=-1 publist_biobib

lint:
	grep -E --color=always -r -i --include=\*.tex --include=\*.bib "(\b[a-zA-Z]+) \1\b" || true

clean:
	rm -f *.aux *.bbl *.blg *.dvi *.idx *.lof *.log *.lot *.toc \
	*.xdy *.nav *.out *.snm *.vrb *.mp \
	*.synctex *.synctex.gz *.brf *.fls *.fdb_latexmk \
	*.glg *.gls *.glo *.ist *.alg *.acr *.acn *.bcf *.xml
	find . -type f -name '*.aux' -delete

realclean: clean
	rm -f cv_duarte_javier*.ps cv_duarte_javier*.pdf publist_biobib*.ps publist_biobib*.pdf PersonalStatement202*.p* VerbiageChair202*.p*
