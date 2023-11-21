set -e

IMAGE_NAME="poetry-arm64-cpython-3.10"
CONTAINER_NAME="yanic-builder"

docker build -t "$IMAGE_NAME" docker/
docker rm -f "$CONTAINER_NAME"
docker run -d --name "$CONTAINER_NAME" -v "./":/app "$IMAGE_NAME"
docker exec "$CONTAINER_NAME" /bin/bash -c "cd app/ && ./container.sh"
docker cp "$CONTAINER_NAME":/app/yanic.pyz "./yanic.pyz"
docker rm -f "$CONTAINER_NAME"
