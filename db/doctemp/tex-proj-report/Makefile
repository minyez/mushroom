PDFNAME = myproject.pdf

PROJNAME = main
MAKE = gmake
LATEXMK = latexmk
LATEX = $(shell \
		  awk '/!TeX TS-program =/ {printf("%s", $$5)}' $(PROJNAME).tex \
		  )
# subdirectories to include in the tarball
SUBDIRS = $(wildcard etc part* appendix)
# all tex sources to let watch work
SOURCES = $(wildcard *.tex) $(wildcard $(patsubst %,%/*.tex,$(SUBDIRS)))
# the bibliography file
BIBFILE = $(PROJNAME).bib
TARBALL = $(PROJNAME).tar.gz
# files to cleanup
AUXSUFFICES = blg,aux,log,out,odt,dvi,dls,fdb_latexmk,synctex.gz,bbl,toc,run.xml,vrb,nav,snm,bcf,fls

# for watching change of tex files
WATCHMAN = watchman-make
WAIT_SETTLE = #-s 1 # waiting time in watchman

.PHONY: default clean veryclean watch dist cleanall

default: $(PDFNAME)

dist: $(TARBALL)

$(PDFNAME): $(PROJNAME).pdf
	cp $< $@

$(PROJNAME).pdf: $(SOURCES)
	$(LATEXMK) -pdf -pdflatex=$(LATEX) -bibtex -f $(PROJNAME).tex \
		-latexoption="-synctex=1 -interaction=nonstopmode -shell-escape "

$(TARBALL): $(PROJNAME).tex $(BIBFILE) $(SUBDIRS) $(PROJNAME).pdf Makefile
	mkdir -p $(PROJNAME)/
	rsync -qazruL --inplace --exclude="*.o" --exclude=".DS_Store" $^ $(PROJNAME)/
	tar -zcvf $@ $(PROJNAME)/
	rm -rf $(PROJNAME)/
	
veryclean: clean
	rm -f $(PROJNAME).pdf $(PDFNAME)
	rm -rf $(TARBALL)

clean:
	rm -f *.{$(AUXSUFFICES)} *-blx.bib
	rm -f */*.{$(AUXSUFFICES)} */*-blx.bib
	rm -rf */_minted-*

cleanall: veryclean

watch:
	$(WATCHMAN) -p $(SOURCES) -t default --make $(MAKE) $(WAIT_SETTLE)
