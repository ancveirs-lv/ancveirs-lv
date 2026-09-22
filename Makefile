.PHONY: check test links

check:
	python scripts/validate_profile.py
	python -m unittest discover -s tests -v
	git diff --check

test:
	python -m unittest discover -s tests -v

links:
	python scripts/check_links.py
