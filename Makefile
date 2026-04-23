.PHONY: ci lint test test-cov test-e2e

ci: lint test

lint:
	ruff check .

test:
	pytest tests/unit tests/integration -x

test-cov:
	pytest tests/unit tests/integration --cov=bureau --cov-report=term-missing --cov-fail-under=80

test-e2e:
	pytest tests/e2e -v
