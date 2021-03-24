PROJNAME = main
PDFNAME = ZhangMY-$(shell date +"%Y%m%d")-slides
MAKE = gmake
LATEXMK = latexmk
LATEX = $(shell \
		  awk '/TeX TS-program =/ {printf("%s", $$5)}' $(PROJNAME).tex \
		  )
# subdirectories to include in the tarball
SUBDIRS = frames etc
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

.PHONY: default clean veryclean watch dist

default: $(PDFNAME).pdf

$(PDFNAME).pdf: $(PROJNAME).pdf
	cp $< $@

dist: $(TARBALL)

$(PROJNAME).pdf: $(SOURCES)
	$(LATEXMK) -pdf -pdflatex=$(LATEX) -bibtex -f $(PROJNAME).tex \
		-latexoption="-synctex=1 -interaction=nonstopmode -shell-escape "

$(TARBALL): $(PROJNAME).tex $(BIBFILE) $(SUBDIRS) $(PROJNAME).pdf
	mkdir -p $(PROJNAME)/
	rsync -qazruL --inplace $^ $(PROJNAME)/
	tar -zcvf $@ $(PROJNAME)/
	rm -rf $(PROJNAME)/
	
veryclean: clean
	rm -f $(PROJNAME).pdf

clean:
	rm -f *.{$(AUXSUFFICES)} *-blx.bib
	rm -f */*.{$(AUXSUFFICES)} */*-blx.bib
	rm -rf */_minted-*
	rm -rf $(TARBALL)

watch:
	$(WATCHMAN) -p $(SOURCES) -t default --make $(MAKE) $(WAIT_SETTLE)
