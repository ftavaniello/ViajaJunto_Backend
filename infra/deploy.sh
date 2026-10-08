#!/bin/sh
set -eu

# Allow diagnostic AWS CLI commands through `docker compose run --rm aws-cli ...`.
if [ "$#" -gt 0 ]; then
    exec aws "$@"
fi

aws --endpoint-url=http://ministack:4566 cloudformation deploy \
    --template-file=/infra/elasticache.yaml \
    --stack-name=viajajunto-cache \
    --no-fail-on-empty-changeset

# MiniStack restores the Redis container lazily after an emulator restart.
aws --endpoint-url=http://ministack:4566 elasticache describe-cache-clusters \
    --cache-cluster-id=viajajunto-demo-cache --show-cache-node-info
aws --endpoint-url=http://ministack:4566 elasticache wait cache-cluster-available \
    --cache-cluster-id=viajajunto-demo-cache
