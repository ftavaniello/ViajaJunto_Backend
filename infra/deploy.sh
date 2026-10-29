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

# Read the live endpoint (the restored container IP can differ from stack outputs).
cache_host=$(aws --endpoint-url=http://ministack:4566 elasticache describe-cache-clusters \
    --cache-cluster-id=viajajunto-demo-cache --show-cache-node-info \
    --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' --output text)
cache_port=$(aws --endpoint-url=http://ministack:4566 elasticache describe-cache-clusters \
    --cache-cluster-id=viajajunto-demo-cache --show-cache-node-info \
    --query 'CacheClusters[0].CacheNodes[0].Endpoint.Port' --output text)
case "$cache_host" in ""|None|redis) echo "Redis nao foi provisionado" >&2; exit 1;; esac
case "$cache_port" in ""|None|*[!0-9]*) echo "Porta Redis invalida" >&2; exit 1;; esac
printf 'redis://%s:%s/0\n' "$cache_host" "$cache_port" > /run/cache/redis-url.tmp
mv /run/cache/redis-url.tmp /run/cache/redis-url
