# ElastiCache local com MiniStack e CloudFormation

ElastiCache oferece armazenamento em memoria para dados temporarios. TTL limita
sua validade; invalidacao remove dados desatualizados. PostgreSQL permanece como
fonte persistente, sem exigir RDS. MiniStack emula a AWS localmente e cria um
Redis real a partir do template CloudFormation `elasticache.yaml`.

## Onde está o ElastiCache?

**O ElastiCache está sendo simulado pelo MiniStack.** Não estamos usando o serviço
real da AWS. O pedido de criação está no arquivo `infra/elasticache.yaml`:

```yaml
Type: AWS::ElastiCache::CacheCluster
Properties:
  Engine: redis
```

Esse trecho significa: **“Crie um recurso ElastiCache que use Redis.”**

| Nome | Papel |
|---|---|
| ElastiCache | Serviço da AWS que administra o cache; aqui é simulado localmente |
| Redis | Programa que efetivamente guarda e consulta os dados do cache |
| MiniStack | Simula o serviço ElastiCache no nosso computador |
| CloudFormation | Recebe a descrição da infraestrutura e coordena sua criação |
| AWS CLI | Envia o comando de deploy e o template ao MiniStack |
| Redis for VS Code / RedisInsight | Interface para visualizar os dados guardados no Redis |

O fluxo no projeto é:

```text
Template CloudFormation: “Quero um ElastiCache com Redis”
                         |
                         v
AWS CLI envia o pedido ao MiniStack
                         |
                         v
MiniStack simula o ElastiCache e cria um container Redis
                         |
                         v
API guarda o total de usuários nesse Redis
                         |
                         v
Extensão do VS Code ou RedisInsight mostra a chave e o valor
```

Por isso vemos **Redis** no Docker e na interface. O **ElastiCache é o serviço
simulado que cria e administra esse Redis**; não existe outro container separado
chamado “ElastiCache”.

Na AWS real, a AWS cuidaria dessa infraestrutura. Na nossa demonstração local,
o MiniStack faz a simulação usando Docker. A API se conecta ao Redis para
armazenar e consultar a contagem; o AWS CLI é usado para provisionar a infraestrutura.

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

O antigo `cache-init demo` foi removido. Agora o endpoint protegido
`GET /usuarios/resumo` usa o Redis real. Veja a demonstracao com a API abaixo.

## Demonstracao do cache com requisicoes reais

Inicie tudo na raiz: `docker compose up -d --build`.

O AWS CLI cria o ElastiCache e grava seu endereco atual no volume `cache-endpoint`.
A API le esse endereco em `REDIS_URL_FILE`. Nao existe um novo container para isso.
Somente a contagem de usuarios e guardada, na chave `viajajunto:usuarios:total:v1`.
Nao sao guardados emails, senhas ou tokens.

### Preparação para quem acabou de baixar o projeto

- Tenha Docker Desktop aberto, com o motor Linux em execução, e Docker Compose disponível.
- Abra no VS Code a pasta `ViajaJunto_Backend`, onde está `docker-compose.yml`.
- Use um terminal PowerShell nessa pasta. Para executar pelo Docker, não precisa ativar
  um venv nem instalar Python ou Redis no Windows.
- Na primeira execução, é necessária internet para baixar as imagens e dependências.
- Se precisar configurar o ambiente, copie `.env.example` para `.env` apenas se
  ainda não tiver esse arquivo. Preserve as configurações existentes.

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d --build
docker compose ps -a
```

Espere o deploy terminar. O serviço `aws-cli` deve aparecer como `Exited (0)`;
isso é sucesso, não erro. Abra http://localhost:8000/health e confira
`{"status":"ok"}`. O Redis criado pelo MiniStack aparece em `docker ps`,
mas não necessariamente em `docker compose ps`, porque não é um serviço
declarado diretamente no Compose.

### Conectar o Redis no VS Code

1. Abra Extensões com `Ctrl+Shift+X`.
2. Instale [Redis for VS Code](https://marketplace.visualstudio.com/items?itemName=Redis.redis-for-vscode),
   publicada pela **Redis**.
3. Confirme a porta do Redis no PowerShell:

```powershell
docker port ministack-elasticache-000000000000-us-east-1-viajajunto-demo-cache 6379/tcp
```

Se esse nome não existir, execute `docker ps`, localize o container de cache
criado pelo MiniStack e use seu nome no comando. Se a saída for
`0.0.0.0:16380`, use a porta **16380**. Esse número é um exemplo:
a porta pode mudar entre computadores ou recriações.

4. Na extensão, escolha **Add Redis database** e preencha:

| Campo | Valor |
|---|---|
| Host | `localhost` |
| Port | A porta retornada pelo comando |
| Database Alias | `ViajaJunto local` (apenas o nome da conexão) |
| Username e Password | Vazios, para este ambiente local |
| Use TLS / Use SSH Tunnel | Desmarcados |
| Database, se solicitado | `0` |

5. Conecte e abra a lista de chaves. Ela pode estar vazia: o deploy cria o Redis,
   mas a chave só é preenchida quando alguém consulta `GET /usuarios/resumo`.

Estas instruções consideram a extensão rodando no VS Code do Windows.
Use a porta publicada no Windows, não o IP interno `172.x.x.x` usado pela API.
Não é necessário criar conta no Redis Cloud nem adicionar outro container.

### Pelo Swagger: criar conta e consultar o resumo

1. Abra http://localhost:8000/docs.
2. Expanda **POST /usuarios**, clique em **Try it out**, preencha e clique em **Execute**:

```json
{
  "nome": "Colega Demo",
  "email": "colega-demo-1@example.com",
  "senha": "SenhaDemo123!"
}
```

Use um email diferente se esse já estiver cadastrado. Essa é uma conta de teste;
o resultado esperado é HTTP **201**. A senha de exemplo é somente para a demonstração local.

3. Em **POST /auth/login**, use o mesmo email e senha:

```json
{
  "email": "colega-demo-1@example.com",
  "senha": "SenhaDemo123!"
}
```

4. Copie apenas o valor de `access_token`, sem aspas. Clique em **Authorize**,
   cole o token no campo, confirme e feche a janela.
5. Execute **GET /usuarios/resumo**. O resultado deve ser HTTP **200**, por exemplo:

```json
{"total_usuarios": 2}
```

O número depende das contas existentes no banco, incluindo dados iniciais e contas
criadas por outros testes. Não precisa ser exatamente 2.

6. Em **Response headers**, procure `x-cache: MISS`.
7. No VS Code, abra **ViajaJunto local**, atualize a lista de chaves e procure:

```text
viajajunto:usuarios:total:v1
```

8. Clique na chave: seu valor deve ser igual ao total retornado pela API.
   O **TTL** indica quantos segundos faltam para ela expirar.
9. Execute **GET /usuarios/resumo** novamente antes da expiração:
   o header deve mostrar `x-cache: HIT`.

Se outra requisição já preencheu o cache, a primeira consulta pode ser HIT.
Aguarde o TTL vencer ou cadastre uma nova conta para invalidar o valor.
O TTL não é renovado em um HIT. Atualize a extensão para ver o estado atual;
a tela aberta pode ainda mostrar um valor que já expirou.

### Testar expiração, invalidação e atualização

Faça os testes um de cada vez, sem outras pessoas consultando a mesma API.

| Teste | O que fazer | Resultado esperado |
|---|---|---|
| Expiração | Consulte o resumo, espere o TTL vencer (padrão: 60 s) sem consultar novamente e atualize a extensão | A chave desaparece |
| Recriação | Consulte o resumo após a expiração | MISS; a chave reaparece com um novo TTL |
| Invalidação por cadastro | Com a chave presente, cadastre outra conta, por exemplo `colega-demo-2@example.com`, e atualize a extensão antes de consultar o resumo | A chave desaparece |
| Total atualizado | Consulte o resumo com a primeira conta | MISS e total aumentado em 1; a chave reaparece com esse valor |
| Reutilização | Consulte de novo antes de expirar | HIT com o mesmo total |
| Invalidação por exclusão | Faça login com a segunda conta, troque o token no Authorize e execute DELETE /usuarios/me | HTTP 204 e chave removida |
| Total após exclusão | Volte ao token da primeira conta e consulte o resumo | MISS e total reduzido em 1 |
| Proteção de acesso | Tente consultar o resumo usando o token da conta excluída | HTTP 401, mesmo que o cache esteja preenchido |

**DELETE /usuarios/me exclui a conta do token atualmente autorizado.**
Use somente contas criadas para este teste. Ao terminar, você pode excluir
a primeira conta de demonstração também, autorizando com o token dela.

Para apresentar o resultado, mostre o JSON e o header X-Cache no Swagger,
depois a chave, o valor e o TTL no VS Code.

### Se algo não funcionar

| Sintoma | O que conferir |
|---|---|
| A extensão não conecta | Docker em execução, Redis presente em `docker ps`, porta atual obtida com `docker port`, host localhost, sem senha/TLS |
| A lista está vazia | Database 0 selecionado, chamada autenticada ao resumo realizada, lista atualizada e TTL ainda não vencido |
| O Swagger retorna 401 | Faça login novamente e use um token válido de uma conta que ainda existe |
| Cadastro retorna 400 | Confira a mensagem: o email pode já estar cadastrado |
| Validação retorna 422 | Confira o formato do email e a senha, com pelo menos oito caracteres |
| X-Cache retorna BYPASS | A API usou o banco; confira os logs e a conexão com o Redis |
| O novo endpoint não aparece | Confirme que está com o código atualizado e execute `docker compose up -d --build` |
| O total não é o esperado | Ele inclui todas as contas; compare a variação após cadastrar/excluir uma conta |
| O comando Docker fica parado | Teste `docker info` e confira se o Docker Desktop terminou de iniciar |

Comandos para diagnóstico, na raiz do projeto:

```powershell
docker compose ps -a
docker ps
docker compose logs --tail 50 aws-cli
docker compose logs --tail 50 api
docker compose logs --tail 50 ministack
```

Se o Redis foi recriado, execute `docker compose run --rm aws-cli` para atualizar
o endereço compartilhado com a API e confira novamente a porta na extensão.
Não é necessário apagar os volumes do banco para refazer o teste.

### O que significa cada resultado

- MISS: a API contou os usuarios no PostgreSQL e gravou o resultado no Redis.
- HIT: a API recuperou a contagem do Redis, sem executar a consulta COUNT.
- BYPASS: cache desativado ou indisponivel; o resultado veio do PostgreSQL.

A autenticacao sempre valida o JWT e a existencia da conta no PostgreSQL,
inclusive em um HIT. Um usuario excluido nao pode usar um token antigo para
acessar o resumo. O corpo nao muda conforme a origem; X-Cache serve para observar
o cache. Cache-Control: no-store impede guardar a resposta em caches HTTP.

### Validade e indisponibilidade

CACHE_TTL_SECONDS configura a validade (padrao: 60 segundos). Cadastro e exclusao
tentam remover a chave depois de confirmar a alteracao no banco.
Se o Redis falhar, a API continua respondendo pelo banco, com timeouts de 0,5 s
por operacao de cache e sem repeticoes automaticas. Falhas de invalidacao sao
registradas no log; uma contagem antiga pode permanecer ate seu TTL vencer.
Alteracoes diretas no banco tambem dependem do TTL. Requisicoes simultaneas podem
repopular um valor antigo durante uma alteracao: este resumo tem consistencia
eventual, e nao deve ser usado para decisoes que exijam contagem exata instantanea.

Para observar a chave, encontre o nome do container Redis com `docker ps` e use:

```powershell
docker exec <nome-do-container-redis> redis-cli GET viajajunto:usuarios:total:v1
docker exec <nome-do-container-redis> redis-cli TTL viajajunto:usuarios:total:v1
```

Para executar a API fora do Docker, defina REDIS_URL com um endereco acessivel
pela maquina. Sem REDIS_URL ou REDIS_URL_FILE, o cache fica desativado (BYPASS).

### Testes

O CI inicia PostgreSQL e Redis para os testes. TEST_REDIS_URL e separado de
REDIS_URL: os testes usam chaves exclusivas e um banco SQLite isolado para
verificar as rotas, sem alterar usuarios reais. Os testes existentes de
persistencia continuam verificando PostgreSQL.

Os testes verificam MISS/HIT, ausencia de COUNT em um HIT, TTL, invalidacao apos
cadastro/exclusao, rejeicao de token invalido e de conta excluida, valor de cache
invalido e resposta pelo banco quando Redis esta indisponivel.

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
