.PHONY: test style default

default:
	@$(MAKE) -k test style || (echo "Some checks failed. Fix issues above." && exit 1)
	@echo "All checks passed!"

test:
	pytest

style:
	pylint src/mirrsearch tests
