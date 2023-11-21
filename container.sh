set -e

poetry install --only build
poetry run shiv . --reproducible --compressed -p '/usr/bin/python3 -sE' -e yanic.server:main -o yanic.pyz
