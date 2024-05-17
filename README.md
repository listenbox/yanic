# Yanic

Async [yt-dlp](https://github.com/yt-dlp/yt-dlp) server

[HTTP protocol](yanic.kdl)

## Why

Spawning a new Python interpreter for each download is slow

## Dev Environment

```sh
brew install go-task pipx
pipx install poetry
```

## Development

```sh
task poetry
task start
```

### Testing

Uses [ResponsibleAPI](https://responsibleapi.com/) to verify the server,
requires [bunx from Bun](https://bun.sh/docs/cli/bunx) or [npx from node.js](https://docs.npmjs.com/cli/v9/commands/npx)
to compile the protocol to `openapi.json`

```sh
task openapi.json
task tests
```

## Deployment

Uses [shiv](https://github.com/linkedin/shiv) to build a [zipapp](https://docs.python.org/3/library/zipapp.html).
Modify `--platform manylinux2014_x86_64 --python-version 310` to your needs in the [Taskfile](Taskfile.yml)

```sh
task build
# rsync yanic.pyz to server
PORT=8006 ./yanic.pyz
```

Yanic is leaking memory, and is [killed every N requests](yanic/server.py).
See [Uvicorn --limit-max-requests](https://www.uvicorn.org/settings/#resource-limits).
Use [systemd](https://systemd.io/) or something similar to restart it.
