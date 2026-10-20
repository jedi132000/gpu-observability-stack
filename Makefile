.PHONY: install lint type test check validate demo demo-down

install:
	pip install -e '.[dev]'

lint:
	ruff check src tests

type:
	mypy

test:
	pytest -q

check: lint type test

# Static validation of rules and dashboards (uses gpuobs; promtool if present).
validate:
	./scripts/validate.sh

demo:
	docker compose -f examples/docker-compose.yaml up -d

demo-down:
	docker compose -f examples/docker-compose.yaml down
