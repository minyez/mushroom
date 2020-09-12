PROJ = mushroom
VERSION = 0.0.1
MESSAGE_FILE = message.txt
DIST_TARBALL = dist/$(PROJ)-$(VERSION).tar.gz

include .objects

.PHONY: dist clean

dist: $(DIST_TARBALL)

$(DIST_TARBALL): $(DIST_FILES)
	find . -name "*.log" -delete
	mkdir -p dist/$(PROJ)-$(VERSION)
	cp -r $^ dist/$(PROJ)-$(VERSION)/
	cd dist; tar --exclude=".DS_Store" \
		--exclude="*.pyc" \
		--exclude="__pycache__" \
		--exclude=".pytest_cache" \
		-zcvf $(PROJ)-$(VERSION).tar.gz $(PROJ)-$(VERSION)
	rm -rf dist/$(PROJ)-$(VERSION)

clean:
	rm -rf dist

test:
	@echo "Run pytest"; pytest --cov=./

commit:
	git commit -F $(MESSAGE_FILE)
