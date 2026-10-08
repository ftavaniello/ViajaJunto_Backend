# ElastiCache local com MiniStack e CloudFormation

ElastiCache oferece armazenamento em memoria para dados temporarios. TTL limita
sua validade; invalidacao remove dados desatualizados. PostgreSQL permanece como
fonte persistente, sem exigir RDS. MiniStack emula a AWS localmente e cria um
Redis real a partir do template CloudFormation `elasticache.yaml`.

## Inicializacao

Na raiz do repositorio, com Docker Desktop em modo Linux:

```powershell
docker compose up -d --build
```

Ordem definida com `depends_on`:

1. MiniStack inicia e passa no healthcheck.
2. AWS CLI executa `cloudformation deploy` no endpoint local, consulta o ElastiCache
   para restaurar o Redis apos reinicios e aguarda o cluster ficar disponivel.
3. Apos sucesso do deploy, PostgreSQL inicia e passa no healthcheck.
4. O container da API executa `alembic upgrade head`.
5. Somente se as migracoes passarem, Uvicorn inicia a API.

AWS CLI e uma tarefa temporaria: `Exited (0)` significa sucesso. O deploy aceita
uma stack existente sem alteracoes. Falhas no deploy bloqueiam a inicializacao
dos dependentes. As migracoes rodam no proprio container da API.

Ficam em execucao MiniStack, PostgreSQL, API e o Redis criado pelo ElastiCache.
Nao ha Redis auxiliar nem provisionador Python. O volume `ministack-state`
guarda snapshots do emulador; volume nao e container. O MiniStack usa o socket
Docker para criar o cache na rede `viajajunto-cache-local`.
As credenciais `test` sao ficticias; esta configuracao e para uso local.

## Conferir

```powershell
docker compose ps -a
docker compose logs aws-cli api
docker compose run --rm aws-cli --endpoint-url=http://ministack:4566 cloudformation describe-stacks --stack-name viajajunto-cache
docker compose run --rm aws-cli --endpoint-url=http://ministack:4566 elasticache describe-cache-clusters --show-cache-node-info
```

Confira `CREATE_COMPLETE` ou `UPDATE_COMPLETE` e outputs `CacheHost`/`CachePort`.
Para reaplicar somente o template: `docker compose run --rm aws-cli`.

O antigo `cache-init demo` foi removido. O cache ainda nao esta integrado aos
endpoints. Provisionar infraestrutura nao comprova HIT/MISS em requisicoes da API.

## Encerrar

Exclua a stack enquanto MiniStack ainda esta rodando:

```powershell
docker compose run --rm aws-cli --endpoint-url=http://ministack:4566 cloudformation delete-stack --stack-name viajajunto-cache
docker compose run --rm aws-cli --endpoint-url=http://ministack:4566 cloudformation wait stack-delete-complete --stack-name viajajunto-cache
docker compose down
```

Nao use `down -v` se quiser preservar os dados do PostgreSQL.

## Apresentacao

Explique cache, TTL, invalidacao e banco como fonte persistente. Mostre o template,
o deploy pelo AWS CLI, os outputs e o Redis criado. A emulacao nao demonstra alta
disponibilidade ou desempenho de um ambiente AWS de producao.

Referencias: [MiniStack](https://ministack.org/docs/cloudformation) e
[AWS CLI em Docker](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-docker.html).
