PROJ = mushroom
VERSION = 0.0.1
MESSAGE_FILE = mcm.info
DIST_TARBALL = dist/$(PROJ)-$(VERSION).tar.gz
SED = gsed

include .objects

.PHONY: default dist clean test commit

default: test

dist: $(DIST_TARBALL)

$(DIST_TARBALL): $(DIST_FILES)
	$(MAKE) clean
	mkdir -p dist/$(PROJ)-$(VERSION)
	cp -r $^ dist/$(PROJ)-$(VERSION)/
	$(SED) "/CircleCI/d;/codecov/,+1 d" README.md > dist/$(PROJ)-$(VERSION)/README.md
	cd dist; tar --exclude=".DS_Store" \
		--exclude="*.pyc" --exclude="__pycache__" \
		--exclude="*.log" \
		--exclude=".git*" \
		--exclude="vasp_*/vasp.sh" \
		--exclude="*_*/common.sh" \
		--exclude=".pytest_cache" \
		-zcvf $(PROJ)-$(VERSION).tar.gz $(PROJ)-$(VERSION)
	rm -rf dist/$(PROJ)-$(VERSION)

clean:
	find . -name "*.log" -delete
	find . -name ".coverage" -delete
	rm -rf dist

test:
	@echo "Run pytest"; pytest --cov=./

commit:
	git commit -F $(MESSAGE_FILE)
	rm -f $(MESSAGE_FILE); touch $(MESSAGE_FILE)


amend:
	git commit --amend
