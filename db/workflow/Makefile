WORKFLOWS = vasp_gw_conv

TARBALL_SUFFIX = tar.gz

TARGETS = $(patsubst %,%.$(TARBALL_SUFFIX),$(WORKFLOWS))

%.tar.gz: %
	tar -zcLf $@ $^

clean:
	rm -f *.$(TARBALL_SUFFIX)
