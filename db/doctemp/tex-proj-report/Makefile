LATEX = $(shell \
		  awk '/TS-program =/ {printf("%s", $$5)}' main.tex \
		  )
MAKE = gmake
# for watching change of tex files
WATCHMAN = watchman-make

.PHONY: default clean veryclean watch

default: main.pdf

main.pdf: main.tex
	latexmk -latexoption="-synctex=1 -interaction=nonstopmode -shell-escape " -pdf -pdflatex=$(LATEX) -bibtex -f $<

veryclean: clean
	rm -f *.pdf *.tex

clean:
	rm -rf *.blg *.aux *.out *.odt *.log *.dvi *.fls *.fdb_latexmk *.synctex.gz \
		_minted-* *.bbl *.toc \
		*.run.xml *.vrb *.nav *.snm *.bcf

watch:
	$(WATCHMAN) -p '**/*.tex' -t default --make $(MAKE)
