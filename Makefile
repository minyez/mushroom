PROJ = mushroom
# get version from __init__ file
VERSION = $(shell \
		  awk '/__version__/ {printf("%s", $$3)}' $(PROJ)/__init__.py | sed -e 's/"//g' \
		  )
BUILDTIME = $(shell date +'%Y-%m-%d %H:%M:%S')
MESSAGE_FILE = mcm.info
AWK = gawk
MAKE = gmake
DIST_TARBALL = dist/$(PROJ)-$(VERSION).tar.gz
DIST_TARBALL_TEST = dist/$(PROJ)-$(VERSION)-test.tar.gz
SED = gsed
CHANGELOG_FILE = ./doc/changelog.rst
GIT_TODAY_CHANGE = $(strip $(shell awk "/$$(date +"%Y-%m-%d")/" $(CHANGELOG_FILE)))
GIT = git

include .objects

.PHONY: default distrc push clean remote pytest test commit amend version dist

default: pytest

clean:
	find . -name "*.log" -delete
	find . -name ".coverage" -delete
	rm -rf dist

pytest:
	$(MAKE) clean
	@echo "Run pytest"; pytest --cov=./

test: pytest remote

dist: pytest
	$(MAKE) $(DIST_TARBALL)

remote: $(DIST_TARBALL_TEST)
	scripts/dist_rsync.py --test

commit:
ifeq ($(GIT_TODAY_CHANGE),)
	@echo "Today's change log is not found in $(CHANGELOG_FILE). Please update!"; exit 1
else
	@$(AWK) "/$$(date +"%Y-%m-%d")/,EOF" $(CHANGELOG_FILE) | sed -e '0,/^-\+/d' -e '/[0-9]\{4\}-/Q' > $(MESSAGE_FILE)
	$(MAKE) pytest
	@$(GIT) add $(CHANGELOG_FILE)
	@$(GIT) commit -F $(MESSAGE_FILE)
endif
	rm -f $(MESSAGE_FILE); touch $(MESSAGE_FILE)

amend: pytest
	@$(GIT) add $(CHANGELOG_FILE)
	$(GIT) commit --amend

push:
	@$(GIT) push origin master

$(DIST_TARBALL): $(DIST_FILES)
	mkdir -p dist/$(PROJ)
	cp -r $^ dist/$(PROJ)/
	$(SED) "/CircleCI/d;/codecov/,+1 d;s/build time/build time: $(BUILDTIME)/g" \
		README.md > dist/$(PROJ)/README.md
	cd dist; tar --exclude=".DS_Store" \
		--exclude="*.pyc" --exclude="__pycache__" \
		--exclude="*.log" \
		--exclude=".git*" \
		--exclude="vasp_*/vasp.sh" \
		--exclude="*_*/common.sh" \
		--exclude=".pytest_cache" \
		-zcvf $(shell basename $@) $(PROJ)
	rm -rf dist/$(PROJ)

$(DIST_TARBALL_TEST): $(DIST_FILES) prototype
	mkdir -p dist/$(PROJ)
	cp -r $^ dist/$(PROJ)/
	$(SED) "/CircleCI/d;/codecov/,+1 d;s/build time/build time: $(BUILDTIME)/g" \
		README.md > dist/$(PROJ)/README.md
	cd dist; tar --exclude=".DS_Store" \
		--exclude="*.pyc" --exclude="__pycache__" \
		--exclude="*.log" \
		--exclude=".git*" \
		--exclude="vasp_*/vasp.sh" \
		--exclude="*_*/common.sh" \
		--exclude=".pytest_cache" \
		-zcvf $(shell basename $@) $(PROJ)
	rm -rf dist/$(PROJ)

distrc:
	scripts/dist_rsync.py --rc

