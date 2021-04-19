.PHONY: default clean veryclean

GRACEBAT = gracebat -hardcopy -hdevice EPS -pipe
# clean up grace eps if eps2eps can be found
EPS2EPS = eps2eps
AGRSRCS = $(wildcard *.agr)
EPSOBJS = $(patsubst %.agr,%.eps,$(AGRSRCS))
PNGOBJS = $(patsubst %.agr,%.png,$(AGRSRCS))
PDFOBJS = $(patsubst %.agr,%-eps-converted-to.pdf,$(AGRSRCS))

default: $(EPSOBJS)

clean:
	rm -f *eps-converted-to.pdf
	rm -f $(PNGOBJS) $(PDFOBJS)

veryclean: clean
	rm -f $(EPSOBJS)

%.eps: %.agr
	$(GRACEBAT) -printfile $@ < $<
ifneq (, $(shell which $(EPS2EPS)))
	$(EPS2EPS) $@ $@_cu; mv $@_cu $@
endif
