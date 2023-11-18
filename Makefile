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
	poetry run shiv . --reproducible --compressed -p '/usr/bin/python3 -sE' -e yanic.server:main -o yanic.pyz --only-binary=:all: --platform manylinux2014_x86_64 --python-version 3.10

.PHONY: schemathesis
schemathesis: openapi.json
	poetry run st run --checks all --base-url http://localhost:8006 --workers 40 ./openapi.json

.PHONY: deploy
deploy: tests build
	@$(MAKE) -f prod.mk deploy

.PHONY: logs
logs:
	@$(MAKE) -f prod.mk logs

.PHONY: reinstall-poetry
reinstall-poetry:
	curl -sSL https://install.python-poetry.org | python3 - --uninstall
	curl -sSL https://install.python-poetry.org | python3 -
