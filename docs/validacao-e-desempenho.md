# Validação integrada e desempenho do backend

Referências: RNF02 (páginas em menos de 3 segundos) e RNF03 (hash, JWT e isolamento).
Este guia reúne os cenários de validação e a reprodução da medição HTTP.
Os dados de desempenho versionados são uma medição histórica; o CI publica novos
resultados a cada execução. O contrato atual é o OpenAPI gerado pela aplicação.

## Fluxo integrado

`tests/integration/consolidacao/test_fluxo_integrado.py` executa, pela API:

1. Cadastro de criador e colaborador, verificação de hash bcrypt e login com JWT real.
2. Criação de viagem e recusa de acesso antes do convite.
3. Envio de convite, captura do link, aceite como Visualizador e promoção a Editor.
4. Inclusão de destino e atividade, orçamento e conferência exata de custos e saldo.
5. Recusa de review antes da conclusão, conclusão de atividade e viagem e avaliação.
6. Consulta pública da média e reviews, sem dados privados do roteiro.
7. Consulta de viagens compartilhadas e notificações, remoção do membro e perda de
   acesso usando o mesmo JWT; logout e recusa da sessão encerrada.

PostgreSQL, repositórios, UnitOfWork, hash e JWT são reais. Apenas o transporte de
email é substituído por `EmailSenderMemory`, evitando enviar mensagens externas.
O teste não depende do seed. Cada cenário usa uma transação externa com rollback.

## Matriz de autorização

A matriz enumera todas as operações privadas publicadas no OpenAPI. Um teste
compara o inventário: adicionar uma operação privada exige atualizar os cenários.
Para cada operação usa Criador, Editor, Visualizador, usuário externo à viagem,
usuário removido com JWT anterior, visitante e token inválido.

| Recurso | Criador | Editor | Visualizador | Externo/removido |
| --- | --- | --- | --- | --- |
| Viagem, roteiro, atividades, orçamento e mapa: leitura | Permite | Permite | Permite | 404 |
| Dados gerais, destinos, atividades e orçamento: escrita | Permite | Permite | 403 | 404 |
| Excluir viagem e gerir convites/membros | Permite | 403 | 403 | 404 |
| Avaliar ocorrência concluída | Permite | Permite | Permite | 404 |
| Conta, lista pessoal e notificações próprias | Próprias | Próprias | Próprias | Próprias |

Visitante e JWT inválido recebem `401` em todas as operações privadas. Aceitar um
convite depende do email destinatário, não do papel em outra viagem. A exclusão de
conta respeita a política da #30, incluindo `409` para criador com colaboradores.

Os testes também misturam IDs de viagens, paradas, atividades, convites e membros,
inclusive com um criador que tem acesso legítimo às duas viagens: isso comprova
que o recurso filho pertence ao contexto informado. Notificações de outro usuário
retornam `404`. Negativas comparam o estado das tabelas antes e depois, para
verificar ausência de alterações. As listas pessoais verificam o conteúdo retornado.

## Migrações

- Instalação de toda a cadeia em schema vazio, conferindo tabelas e versão `head`,
  sem contas/viagens inseridas pela migração.
- Atualização real desde `a3f1c9d27b45` (modelo v1) com contas, participação,
  catálogo, roteiro, custo, comprovação, orçamento e review já gravados.
- Preservação de IDs, autoria, senha, observações, valores e datas; conversão
  prevista de `em_andamento` para `confirmada` e `realizada` para `concluida`.
- Preservação de identificadores externos legados com fonte `manual`, conforme a
  migração existente; reaplicação de `head` sem duplicação.

Os testes específicos de migrações já existentes continuam na suíte. Essas bases
são schemas descartáveis com nomes aleatórios, exclusivamente em PostgreSQL cujo
nome termina em `_test`. O schema público e o banco de desenvolvimento não são
reiniciados. A limpeza ocorre também quando um cenário falha.

## Medição do backend

Resultado bruto: [desempenho-backend.json](resultados/desempenho-backend.json).

Data UTC: **2026-11-05T00:47:01.651685+00:00**. Ambiente: **Windows-10-10.0.19045-SP0**, Python **3.13.1**,
CPU **Intel64 Family 6 Model 142 Stepping 12, GenuineIntel**, **8** processadores lógicos;
PostgreSQL **PostgreSQL 16.15 (Debian 16.15-1.pgdg13+2) on x86_64-pc-linux-gnu**.
Servidor Uvicorn com um worker, PostgreSQL em Docker, HTTP TCP em loopback.
Recursos do host são compartilhados e não há limites de CPU/memória controlados.

Dataset sintético criado do zero para cada execução:

- 50 usuários; 2.000 viagens; 588 participações; 2.000 orçamentos.
- 50 destinos e 1.000 atividades públicas.
- 2.000 paradas e 11.000 atividades de roteiro; a viagem do resumo tem 1.005 atividades.
- 20.000 avaliações públicas (20 por atividade), com notas de 1 a 5.
- Usuário da lista: 40 viagens próprias e 588 compartilhadas, permitindo testar página 10.

São 100 requisições por endpoint e nível de concorrência (1 e 5), totalizando
1.400 requisições medidas, mais cinco de aquecimento por cenário. Percentis pelo
método nearest rank. O tempo inclui conexão HTTP, JWT, banco, aplicação e
serialização; login/bcrypt e envio de email ficam fora. O cliente `urllib` não
mantém pool de conexões HTTP. Cache da contagem de usuários em **BYPASS**, para
incluir consulta ao banco. As respostas são verificadas (status, tamanho das
páginas, soma financeira e contagem de usuários), além do tempo.

| Endpoint | Concorrência | p50 ms | p95 ms | Máximo ms | Erros |
| --- | ---: | ---: | ---: | ---: | ---: |
| `/viagens?pagina=1&tamanho_pagina=20` | 1 | 14.31 | 33.24 | 37.02 | 0 |
| `/viagens?pagina=10&tamanho_pagina=20` | 1 | 11.86 | 33.79 | 56.61 | 0 |
| `/catalogo/atividades?tamanho_pagina=20` | 1 | 8.37 | 34.09 | 45.47 | 0 |
| `/catalogo/atividades?nota_minima=4&tamanho_pagina=20` | 1 | 11.05 | 31.14 | 33.08 | 0 |
| `/catalogo/atividades?localizacao=Roma&tamanho_pagina=20` | 1 | 15.12 | 34.34 | 40.23 | 0 |
| `/viagens/1/orcamento` | 1 | 13.98 | 40.79 | 84.79 | 0 |
| `/usuarios/resumo` | 1 | 9.44 | 32.02 | 57.74 | 0 |
| `/viagens?pagina=1&tamanho_pagina=20` | 5 | 31.92 | 53.34 | 69.25 | 0 |
| `/viagens?pagina=10&tamanho_pagina=20` | 5 | 41.68 | 53.67 | 75.29 | 0 |
| `/catalogo/atividades?tamanho_pagina=20` | 5 | 34.44 | 39.66 | 54.92 | 0 |
| `/catalogo/atividades?nota_minima=4&tamanho_pagina=20` | 5 | 35.88 | 64.85 | 73.59 | 0 |
| `/catalogo/atividades?localizacao=Roma&tamanho_pagina=20` | 5 | 47.66 | 71.06 | 113.61 | 0 |
| `/viagens/1/orcamento` | 5 | 37.85 | 46.70 | 69.43 | 0 |
| `/usuarios/resumo` | 5 | 34.19 | 55.34 | 89.81 | 0 |

Neste cenário não houve erros nem gargalo que justificasse alterar consultas ou
adicionar índices. Os testes de contagem de SQL também verificam que aumentar a
página de 1 para 20 itens não gera uma consulta adicional por item (N+1) em listas
de viagens e catálogo. Isso não demonstra custo constante com o crescimento do banco.

**A medição não comprova integralmente o RNF02:** não inclui navegador, renderização,
frontend, rede externa, TLS ou balanceador. Usa carga fechada (até cinco requisições
simultâneas, repondo após resposta) e buffers/pool aquecidos. Não é teste de estresse,
partida a frio ou capacidade máxima, nem representa latência de produção. O tempo
completo da página deve ser medido na integração com o frontend e sua rede.

## CI e reprodução

O workflow de testes executa a suíte inteira com PostgreSQL e Redis reais,
cobertura de `app` e JUnit. `tests.support.verificar_ci` falha se qualquer módulo de
integração estiver ausente do relatório ou se uma integração for ignorada. A etapa
seguinte repete a medição HTTP e salva os resultados como artefatos, junto da
cobertura e do JUnit. Não há limite de milissegundos no CI: ruído do runner não deve
ser confundido com regressão funcional. Respostas inválidas fazem a medição falhar.
Lint e Spectral passam a executar em PRs para `develop` e `main`.

Exemplo no PowerShell, com as dependências da `.venv` instaladas:

```powershell
docker compose --profile test up -d --wait db_test
docker run -d --rm --name viajajunto-redis-test -p 127.0.0.1:6381:6379 redis:7-alpine
$env:APP_ENV = "test"
$env:TEST_2026-11-05T00:47:01.651685+00:00BASE_URL = "postgresql+psycopg2://viajajunto:viajajunto@localhost:5433/viajajunto_test"
$env:TEST_REDIS_URL = "redis://localhost:6381/15"
$env:JWT_SECRET_KEY = "ci-test-secret-key-com-pelo-menos-32-bytes"
.venv\Scripts\python.exe -m pytest --cov=app --cov-report=xml --junitxml=.cache/junit.xml
.venv\Scripts\python.exe -m tests.support.verificar_ci .cache/junit.xml
.venv\Scripts\python.exe -m tests.performance.medir_backend --amostras 100 --saida .cache/desempenho.json
docker stop viajajunto-redis-test
```

O segredo acima é apenas uma chave de teste. Para executar somente os cenários
novos: `python -m pytest tests/integration/consolidacao`. A auditoria de JUnit exige
a suíte completa, pois verifica a presença de todos os módulos de integração.

## Resultados registrados

Execução original da #31: **1.306 testes aprovados, nenhum ignorado**, com PostgreSQL e
Redis reais. A auditoria de JUnit confirmou a execução de todos os módulos de
integração. Cobertura de linhas de `app`: **97.61%**.
Ruff, sintaxe YAML, imports hexagonais e Spectral passaram; o Spectral conserva
somente os avisos já existentes sobre `servers` e `info.contact`. Os dois avisos
no pytest são os existentes de depreciação do Starlette/anyio e do teste negativo
com algoritmo JWT alternativo.

Os checks remotos, incluindo SonarQube e Trivy, precisam executar no PR. A medição
local documentada permanece como referência; cada execução do CI publica seu
próprio resultado, sem sobrescrever esse arquivo versionado.

Após o alinhamento dos tipos de atividades, a execução local completa registrou
**1.309 testes aprovados**, sem skips; a auditoria confirmou 39 módulos de integração.
Esses números registram aquelas execuções e devem ser atualizados com novas evidências.
A matriz inclui também `tests/integration/test_tipos_atividades_originais.py`, que
verifica conversão de dados legados, hospedagem, filtros e resumo financeiro.

## SonarQube e Quality Gate

O workflow de testes executa o job **SonarQube Quality Gate** após os testes
passarem, em PRs para `main` e pushes nessa branch. O job baixa o `coverage.xml`
da mesma execução e usa `SonarSource/sonarqube-scan-action` para analisar `app/`
e identificar `tests/` como código de teste. A cobertura usa caminhos relativos
para permitir a leitura do relatório em outro job.

O arquivo `sonar-project.properties` identifica o projeto
`ftavaniello_ViajaJunto_Backend`, na organização `ftavaniello`. A opção
`sonar.qualitygate.wait=true` faz o scanner aguardar até 300 segundos pelo
resultado do Quality Gate; reprovação ou falha na análise faz o job falhar.

Configuração externa necessária:

1. No projeto do SonarQube Cloud, desative **Automatic Analysis** em
   **Administration → Analysis Method** para usar a análise pelo CI.
2. Gere um token de análise e cadastre-o no GitHub em
   **Settings → Secrets and variables → Actions**, como secret **SONAR_TOKEN**.
   Nunca coloque o token no repositório.
3. Após a primeira execução, inclua **SonarQube Quality Gate** e o check de testes
   entre os checks obrigatórios da proteção da `main`.

O job falha explicitamente se o token estiver ausente. PRs de forks normalmente
não recebem secrets e, portanto, não conseguem executar essa análise autenticada.

## Build e verificação da imagem Docker

O Dockerfile usa uma etapa de instalação separada e transfere o ambiente Python
para a imagem final sem `pip`, `setuptools` ou `wheel`. Essas ferramentas e suas
dependências internas não são necessárias para iniciar a API ou aplicar as
migrações. Para mudar dependências, reconstrua a imagem; não instale pacotes
manualmente no container em execução.

A base é `python:3.13-alpine`, com atualizações do Alpine e bibliotecas de
execução para PostgreSQL. As dependências são instaladas como pacotes binários
(`--only-binary=:all:`); uma nova dependência sem pacote compatível exigirá
revisar o build. A mudança de Debian para Alpine foi validada em Linux amd64.

Somente `app/`, `alembic/` e `alembic.ini` são copiados para a imagem final.
Os testes continuam no repositório e podem ser montados no container para
validação. O CI usa `pull: true` para consultar a imagem-base atualizada.

O workflow `.github/workflows/ci.yml` constrói a imagem Docker e executa o Trivy
em pushes e pull requests para `main` e `develop`. O check `build-and-scan`
falha quando encontra vulnerabilidades HIGH ou CRITICAL nos pacotes do sistema
operacional ou nas dependências da aplicação, inclusive sem correção disponível.
Vulnerabilidades sem correção não são ignoradas para fazer o CI passar.

Inclua `build-and-scan` nos checks obrigatórios da proteção da `main`.
O workflow também executa em tags `v*` e publica a imagem aprovada pelo Trivy
conforme as regras abaixo.

## Publicação no Docker Hub

Destino: `ftavaniello/viajajunto-backend`.
A publicação usa a mesma imagem local verificada pelo Trivy, sem reconstruí-la.
Se o build ou o scan falhar, as etapas de login e publicação não executam.

| Evento | Tags publicadas |
|---|---|
| Push na `main` (inclusive merge de PR) | `latest` e `sha-<SHA completo>` |
| Push de versão estável, por exemplo `v1.2.3` | `1.2.3`, `latest` e `sha-<SHA completo>` |
| Push de pré-lançamento, por exemplo `v1.2.3-rc.1` | `1.2.3-rc.1` e `sha-<SHA completo>` |
| Push na `develop` ou pull request | Somente build e scan; não publica |

Use tags Git no formato SemVer `vMAJOR.MINOR.PATCH`, com sufixo de
pré-lançamento opcional. A tag `latest` é atualizada por pushes na `main` e por
versões estáveis; ela não é um identificador imutável. Use a versão ou SHA para
selecionar uma publicação específica.

Configure dois **Repository secrets** em
**Settings → Secrets and variables → Actions** no GitHub:

- `DOCKERHUB_USERNAME`: `ftavaniello`.
- `DOCKERHUB_TOKEN`: Access Token do Docker Hub com permissão de leitura e
  escrita no repositório da imagem. Não use a senha da conta nem salve o token
  em arquivos do projeto.

Após o merge na `main`, a publicação de `latest` será automática. Para publicar
uma versão, crie e envie a tag correspondente a um commit aprovado da `main`:

```sh
git switch main
git pull --ff-only origin main
git tag v1.0.0
git push origin v1.0.0
```

O exemplo usa `v1.0.0`; escolha a versão real do projeto. O workflow de imagem
não espera os outros workflows independentes, por isso mantenha os checks
obrigatórios da `main` e publique versões a partir de commits já aprovados.

