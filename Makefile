.PHONY: ci lint test test-cov test-e2e bureau-kafka-up bureau-kafka-down test-kafka-smoke test-kafka-smoke-ts test-kafka-smoke-dotnet

ci: lint test

lint:
	ruff check .

test:
	pytest tests/unit tests/integration -x

test-cov:
	pytest tests/unit tests/integration --cov=bureau --cov-report=term-missing --cov-fail-under=80

test-e2e:
	pytest tests/e2e -v

bureau-kafka-up:
	docker run -d -p 9092:9092 --name bureau-kafka \
		redpandadata/redpanda:latest \
		redpanda start --smp 1 --overprovisioned

bureau-kafka-down:
	docker stop bureau-kafka && docker rm bureau-kafka

test-kafka-smoke:
	BUREAU_KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
		bureau run ../bureau-test-python/specs/001-smoke-hello-world/spec.md \
		--repo ../bureau-test-python

test-kafka-smoke-ts:
	BUREAU_KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
		bureau run ../bureau-test-typescript/specs/001-typed-emitter/spec.md \
		--repo ../bureau-test-typescript

test-kafka-smoke-dotnet:
	BUREAU_KAFKA_BOOTSTRAP_SERVERS=localhost:9092 \
		bureau run ../bureau-test-dotnet/specs/001-kafka-observability-dashboard/spec.md \
		--repo ../bureau-test-dotnet