.PHONY: tests
tests:
	poetry run pytest

.PHONY: start
start:
	poetry run uvicorn yanic.server:app --reload --port 8006 --no-access-log

.PHONY: poetry
poetry:
	poetry show --outdated
	poetry update
	poetry install --sync

openapi.json: yanic.kdl
	bunx @responsibleapi/cli yanic.kdl -o openapi.json

.PHONY: build
build:
	./host.sh

.PHONY: schemathesis
schemathesis: openapi.json
	poetry run st run --checks all --base-url http://localhost:8006 --workers 40 ./openapi.json

.PHONY: deploy
deploy: tests build
	@$(MAKE) -f prod.mk deploy

.PHONY: logs
logs:
	@$(MAKE) -f prod.mk logs
