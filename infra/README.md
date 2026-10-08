# ElastiCache local com CloudFormation e MiniStack

ElastiCache e um servico AWS de armazenamento em memoria. Um cache guarda dados
temporarios para reutilizacao e pode reduzir consultas ao banco. TTL limita o
tempo de vida; invalidacao remove dados quando deixam de representar a origem.
O PostgreSQL continua sendo a fonte persistente e nao precisa estar no RDS.

CloudFormation declara a infraestrutura em YAML. Aqui, o MiniStack recebe essa
declaracao e cria um Redis real em um container Docker para emular ElastiCache.
Isso demonstra provisionamento local, sem criar recursos na AWS.

## Componentes

- `elasticache.yaml`: declara `AWS::ElastiCache::CacheCluster` e exporta endpoint.
- `../docker-compose.yml`: inicia API, PostgreSQL e infraestrutura do cache juntos.
- `../docker-compose.cache.yml`: define os servicos de cache reutilizados pelo Compose principal.
- `ministack-state`: Redis interno do emulador; nao e o cache da aplicacao.
- `cache_local.py`: cria/atualiza a stack e testa o Redis criado por ela.

O MiniStack usa o socket Docker para criar o container de cache na rede
`viajajunto-cache-local`. Esta configuracao e destinada ao ambiente local.
Credenciais `test` sao ficticias, e o endpoint do script aponta apenas ao MiniStack.

## Executar na raiz do repositorio

Com Docker Desktop em modo Linux:

```powershell
docker compose up -d --build
```

O Compose espera o Redis interno ficar saudavel, inicia o MiniStack e aguarda
seu healthcheck. Entao `cache-init` cria/atualiza a stack CloudFormation e confirma
que o cache responde a PING. A API so inicia depois que esse provisionador termina
com sucesso (`service_completed_successfully`) e o PostgreSQL fica saudavel.
Nao e necessario executar `deploy` separadamente. Se o provisionamento falhar,
a inicializacao da API e bloqueada; consulte os logs de `cache-init`.

Para conferir o provisionamento e executar a demonstracao opcional:

```powershell
docker compose logs cache-init
docker compose run --rm cache-init demo
```

O provisionador deve terminar com codigo zero. A demonstracao verifica MISS,
HIT, expiracao por TTL e invalidacao. Sao operacoes Redis isoladas: esta etapa
ainda nao integra cache aos endpoints nem comprova reducao de consultas da API.
Nenhuma dependencia e adicionada ao requirements da aplicacao.

Para reaplicar o template ou consultar a stack:

```powershell
docker compose run --rm cache-init deploy
docker compose run --rm cache-init describe
```

Para remover a infraestrutura, exclua primeiro a stack para que o MiniStack
remova o container que criou:

```powershell
docker compose run --rm cache-init destroy
docker compose down
```

## Roteiro da apresentacao

1. Explicar cache, TTL, invalidacao e o papel do banco como fonte persistente.
2. Mostrar o recurso CloudFormation e os outputs do endpoint.
3. Mostrar a stack criada e o container Redis provisionado pelo MiniStack.
4. Executar `demo` e explicar cada resultado.
5. Explicar que a emulacao local nao demonstra alta disponibilidade, desempenho
   ou controles de seguranca de um ambiente AWS de producao.

Referencias: [MiniStack CloudFormation](https://ministack.org/docs/cloudformation)
e [suporte ElastiCache introduzido em 1.5.20](https://ministack.org/blog/changelog-v1-5-20).
