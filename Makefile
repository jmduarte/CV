tex: cv_duarte_javier_ext cv_duarte_javier publist_biobib PersonalStatement2021

cv_duarte_javier:
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier
	biber cv_duarte_javier
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier

cv_duarte_javier_ext:
	sed -e 's/\setboolean{extended}{false}/\setboolean{extended}{true}/g' cv_duarte_javier.tex > cv_duarte_javier_ext.tex
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier_ext
	biber cv_duarte_javier_ext
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier_ext
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier_ext
	pdflatex -interaction=nonstopmode -synctex=-1 cv_duarte_javier_ext
	rm cv_duarte_javier_ext.tex

publist_biobib:
	pdflatex -interaction=nonstopmode -synctex=-1 publist_biobib
	biber publist_biobib
	pdflatex -interaction=nonstopmode -synctex=-1 publist_biobib
	pdflatex -interaction=nonstopmode -synctex=-1 publist_biobib
	pdflatex -interaction=nonstopmode -synctex=-1 publist_biobib

PersonalStatement2021:
	pdflatex -interaction=nonstopmode -synctex=-1 PersonalStatement2021
	biber PersonalStatement2021
	pdflatex -interaction=nonstopmode -synctex=-1 PersonalStatement2021
	pdflatex -interaction=nonstopmode -synctex=-1 PersonalStatement2021
	pdflatex -interaction=nonstopmode -synctex=-1 PersonalStatement2021

VerbiageChair2021:
		pdflatex -interaction=nonstopmode -synctex=-1 VerbiageChair2021

clip:
	cpdf -i PersonalStatement2021.pdf -range 1-3,65-end -o PersonalStatement2021.pdf

lint:
	grep -E --color=always -r -i --include=\*.tex --include=\*.bib "(\b[a-zA-Z]+) \1\b" || true

clean:
	rm -f *.aux *.bbl *.blg *.dvi *.idx *.lof *.log *.lot *.toc \
	*.xdy *.nav *.out *.snm *.vrb *.mp \
	*.synctex.gz *.brf *.fls *.fdb_latexmk \
	*.glg *.gls *.glo *.ist *.alg *.acr *.acn *.bcf *.xml
	find . -type f -name '*.aux' -delete

realclean: clean
	rm -f cv_duarte_javier*.ps cv_duarte_javier*.pdf publist_biobib*.ps publist_biobib*.pdf PersonalStatement2021*.ps PersonalStatement2021*.pdf
