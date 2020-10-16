PROJ = mushroom
VERSION = 0.0.1
BUILDTIME = $(shell date +'%Y-%m-%d %H:%M:%S')
MESSAGE_FILE = mcm.info
DIST_TARBALL = dist/$(PROJ)-$(VERSION).tar.gz
SED = gsed

include .objects

.PHONY: default dist clean test commit amend

default: test

clean:
	find . -name "*.log" -delete
	find . -name ".coverage" -delete
	rm -rf dist

test:
	$(MAKE) clean
	@echo "Run pytest"; pytest --cov=./

testfarm: test
	$(MAKE) $(DIST_TARBALL)
	scripts/dist_rsync.py

commit: test
	git commit -F $(MESSAGE_FILE)
	rm -f $(MESSAGE_FILE); touch $(MESSAGE_FILE)

amend:
	git commit --amend

dist: $(DIST_TARBALL)
	@git push
	scripts/dist_rsync.py

$(DIST_TARBALL): $(DIST_FILES)
	mkdir -p dist/$(PROJ)
	cp -r $^ dist/$(PROJ)/
	$(SED) "/CircleCI/d;/codecov/,+1 d;s/build time/build time: $(BUILDTIME)/g" \
		README.md > dist/$(PROJ)/README.md
	$(SED) "/testfarm/,+3 d" Makefile > dist/$(PROJ)/Makefile
	cd dist; tar --exclude=".DS_Store" \
		--exclude="*.pyc" --exclude="__pycache__" \
		--exclude="*.log" \
		--exclude=".git*" \
		--exclude="vasp_*/vasp.sh" \
		--exclude="*_*/common.sh" \
		--exclude=".pytest_cache" \
		-zcvf $(PROJ)-$(VERSION).tar.gz $(PROJ)
	rm -rf dist/$(PROJ)

