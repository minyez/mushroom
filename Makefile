PROJ = mushroom
VERSION = 0.0.1
MESSAGE_FILE = message.txt
DIST_FILES = mushroom \
	     examples \
	     doc \
	     tests \
	     workflows \
	     scripts \
	     requirements.txt \
	     LICENSE \
	     TODO.md \
	     Makefile \
	     CHANGELOG \
	     README.md
DIST_TARBALL = dist/$(PROJ)-$(VERSION).tar.gz
ans := "y"


.PHONY: dist clean

dist: $(DIST_TARBALL)

$(DIST_TARBALL): $(DIST_FILES)
	mkdir -p dist/$(PROJ)-$(VERSION)
	cp -r $^ dist/$(PROJ)-$(VERSION)/
	cd dist; tar --exclude=".DS_Store" -zcvf $(PROJ)-$(VERSION).tar.gz $(PROJ)-$(VERSION)
	rm -rf dist/$(PROJ)-$(VERSION)

clean:
	rm -rf dist

test:
	@echo "Run pytest"; pytest --cov=./

commit:
	#@echo "Commit message: $(MESSAGE_FILE)\n"; cat $(MESSAGE_FILE);
	@if [[ ${ans} == "y" ]]; then git commit -F $(MESSAGE_FILE); else echo "\nTo proceed, add ans=y"; fi
