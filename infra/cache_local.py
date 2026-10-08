"""Provisionamento e demonstracao exclusivos do MiniStack local."""

import argparse
import time
import uuid
from pathlib import Path

import boto3
import redis
from botocore.config import Config
from botocore.exceptions import ClientError

STACK = "viajajunto-cache"


def describe(client):
    try:
        return client.describe_stacks(StackName=STACK)["Stacks"][0]
    except ClientError as exc:
        message = exc.response["Error"]["Message"].lower()
        if "does not exist" in message or "not found" in message:
            return None
        raise


def wait_stack(client, deleting=False):
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        stack = describe(client)
        if stack is None:
            if deleting:
                return None
            raise RuntimeError("Stack nao encontrada")
        status = stack["StackStatus"]
        if deleting and status == "DELETE_COMPLETE":
            return None
        if not deleting and status in {"CREATE_COMPLETE", "UPDATE_COMPLETE"}:
            return stack
        if "FAILED" in status or "ROLLBACK" in status:
            raise RuntimeError(client.describe_stack_events(StackName=STACK))
        time.sleep(2)
    raise TimeoutError("CloudFormation nao terminou em 180 segundos")


def connect_cache(stack):
    outputs = {item["OutputKey"]: item["OutputValue"] for item in stack["Outputs"]}
    cache = redis.Redis(
        host=outputs["CacheHost"], port=int(outputs["CachePort"]),
        decode_responses=True, socket_connect_timeout=2, socket_timeout=2,
    )
    deadline = time.monotonic() + 60
    while True:
        try:
            cache.ping()
            print("Redis conectado:", outputs, flush=True)
            return cache
        except redis.RedisError:
            if time.monotonic() >= deadline:
                cache.close()
                raise
            time.sleep(2)


def deploy(client):
    template = Path(__file__).with_name("elasticache.yaml").read_text(encoding="utf-8")
    if describe(client) is None:
        client.create_stack(StackName=STACK, TemplateBody=template)
    else:
        try:
            client.update_stack(StackName=STACK, TemplateBody=template)
        except ClientError as exc:
            if "no updates" not in exc.response["Error"]["Message"].lower():
                raise
    stack = wait_stack(client)
    connect_cache(stack).close()
    print("Stack pronta:", stack["StackStatus"])


def demo(client):
    stack = describe(client)
    if stack is None:
        raise RuntimeError("Execute deploy primeiro")
    cache = connect_cache(stack)
    key = "viajajunto:demo:" + uuid.uuid4().hex
    try:
        assert cache.get(key) is None
        print("MISS: chave ausente")
        cache.set(key, "roteiro-v1", ex=3)
        assert cache.get(key) == "roteiro-v1"
        print("HIT: valor encontrado; TTL:", cache.ttl(key))
        deadline = time.monotonic() + 8
        while cache.exists(key) and time.monotonic() < deadline:
            time.sleep(0.25)
        assert cache.get(key) is None
        print("EXPIRED: chave expirou")
        cache.set(key, "roteiro-v2", ex=30)
        assert cache.get(key) == "roteiro-v2"
        cache.delete(key)
        assert cache.get(key) is None
        print("INVALIDATED: chave removida")
        print("Demonstracao Redis aprovada; nao executa consultas da API/banco.")
    finally:
        cache.delete(key)
        cache.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["deploy", "demo", "describe", "destroy"])
    action = parser.parse_args().action
    client = boto3.client(
        "cloudformation", endpoint_url="http://ministack:4566",
        region_name="us-east-1", aws_access_key_id="test",
        aws_secret_access_key="test",
        config=Config(connect_timeout=5, read_timeout=120, retries={"max_attempts": 2}),
    )
    if action == "deploy":
        deploy(client)
    elif action == "demo":
        demo(client)
    elif action == "describe":
        print(describe(client))
    else:
        client.delete_stack(StackName=STACK)
        wait_stack(client, deleting=True)
        print("Stack removida")


if __name__ == "__main__":
    main()
