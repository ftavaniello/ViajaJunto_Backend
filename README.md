# ViajaJunto — Backend

API de planejamento colaborativo de viagens para a disciplina de Construção de
Software. O backend usa Python 3.13, FastAPI, PostgreSQL e arquitetura hexagonal.
O frontend é desenvolvido separadamente.

## Executar a aplicação

Pré-requisitos: Git, Docker Desktop em modo Linux e Docker Compose v2.
Em um clone novo:

```powershell
git clone https://github.com/ftavaniello/ViajaJunto_Backend.git
cd ViajaJunto_Backend
Copy-Item .env.example .env
docker compose up -d --build
```

Em um checkout existente, mantenha seu `.env` e execute o último comando. Os valores
de exemplo são para desenvolvimento. Configurações estão em [.env.example](.env.example).

| Serviço | Endereço local |
| --- | --- |
| Swagger / OpenAPI | <http://localhost:8000/docs> / <http://localhost:8000/openapi.json> |
| Saúde da API | <http://localhost:8000/health> |
| Emails capturados pelo Mailpit | <http://localhost:8025> |
| PostgreSQL | `localhost:5432`, banco `viajajunto` por padrão |

O Compose provisiona o cache no MiniStack com AWS CLI/CloudFormation, aguarda o
PostgreSQL, aplica Alembic e, em `APP_ENV=development`, executa o seed antes de
iniciar a API. O Redis guarda a contagem de usuários e um snapshot do ranking público de destinos. O passo a passo de
MiniStack, CloudFormation e Redis está em [infra/README.md](infra/README.md).

Para conferir a inicialização:

```powershell
docker compose ps -a
docker compose logs api aws-cli
```

Os dados ficam no volume do PostgreSQL. Reiniciar preserva os dados; o seed é
idempotente. O reset é um comando explícito de desenvolvimento descrito em
[reset-banco.md](docs/reset-banco.md).

## Testar pelo Swagger

No banco novo, entre em `POST /auth/login` com `criador.demo@example.com` e senha
inicial `DemoViaja123!`. Copie o `access_token` para **Authorize**. A conta participa
de roteiros em Orlando, Miami, Rio de Janeiro e Roma. Contas de Editor, Visualizador,
usuário externo e usuário descartável estão em [dados de demonstração](docs/seed-demonstracao.md).

O catálogo é público. Operações privadas identificam o usuário pelo JWT; a API
consulta o vínculo atual a cada operação. Usuários sem acesso à viagem recebem
`404`, e participantes sem permissão para uma alteração recebem `403`.

O [roteiro da demonstração no Swagger](docs/demo-swagger.md) reúne a sequência
de chamadas, parâmetros, corpos JSON e resultados esperados para a apresentação.

## Funcionalidades e guias

| Área | Implementado no backend | Guia |
| --- | --- | --- |
| Autenticação e perfil — RF01–RF03 | Cadastro, login, logout, perfil, troca e recuperação de senha | [Sessões](docs/sessoes-e-logout.md), [recuperação](docs/recuperacao-de-senha.md) |
| Exclusão de conta | Bloqueio de criador com colaboradores; preservação de reviews anônimos | [Exclusão](docs/exclusao-conta.md) |
| Viagens — RF04–RF07 | Criar, consultar, listar próprias/compartilhadas, editar, excluir e definir status | [Permissões e decisões](docs/decisoes-de-produto.md#d4--permissões-por-viagem) |
| Destinos — RF08–RF10 | Catálogo pesquisável e múltiplas paradas com estadias e ordem de visita | [Catálogo](docs/catalogo-destinos.md), [roteiro](docs/destinos-roteiro.md) |
| Mapa — RF11 | Países visitados e pontos ordenados do roteiro para o frontend | [Mapa](docs/mapa-paises-visitados.md) |
| Atividades — RF12–RF14 | Agenda cronológica, data, horário, duração, custo e status | [Atividades do roteiro](docs/atividades-roteiro.md) |
| Orçamento — RF15–RF17 | Limite, custos previstos, saldo e percentuais por tipo | [Orçamento](docs/orcamento-viagem.md) |
| Colaboração — RF18–RF21 | Convites por email, papéis, remoção e notificações in-app por polling | [Convites](docs/convites-e-membros.md), [avisos](docs/decisoes-de-produto.md#d9--email-e-notificacoes) |
| Avaliação e descoberta — RF22–RF25 | Reviews de atividades concluídas, média, busca/filtros e ranking de destinos | [Avaliações](docs/avaliacoes-atividades.md), [catálogo](docs/catalogo-atividades.md), [ranking](docs/ranking-destinos.md) |
| Locais externos | Enriquecimento operacional do catálogo com Geoapify | [Integração](docs/integracao-locais.md) |

O contrato atualizado de métodos, campos, enums e respostas é o OpenAPI da API.
Os tipos são `passeio`, `refeicao`, `hospedagem`, `transporte` e `outro`.
O [guia do catálogo](docs/catalogo-atividades.md#tipos-de-atividades) explica também
a conversão de registros antigos. O catálogo pode ser abastecido por importação JSON
ou pelo operador via Geoapify, preservando IDs e avaliações.

## Organização e arquitetura

```text
app/domain/             Entidades, regras, erros e portas
app/application/        Casos de uso, autorização e coordenação de transações
app/adapters/inbound/    API HTTP e comandos CLI
app/adapters/outbound/   PostgreSQL/memória, segurança, email, cache e locais externos
app/infrastructure/     Configuração, sessões e composição de dependências
alembic/                Evolução do schema
tests/                  Domínio, aplicação, infraestrutura, integração e medição
docs/                   Guias atuais, validação e histórico
infra/                  MiniStack, CloudFormation e demonstração do cache
```

- [Requisitos do produto](docs/requirements-ViajaJunto.md): especificação recebida dos criadores.
- [Arquitetura atual e DER](docs/architecture-ViajaJunto.md): componentes e persistência implementados.
- [Arquitetura hexagonal](ARQUITETURA_HEXAGONAL.md): regras obrigatórias de implementação.
- [Decisões de produto](docs/decisoes-de-produto.md): interpretações adotadas e adaptações da especificação.

## Testes e checks

Para executar no host, instale Python 3.13 e prepare o ambiente virtual:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
docker compose --profile test up -d --wait db_test
docker run -d --rm --name viajajunto-redis-test -p 127.0.0.1:6381:6379 redis:7-alpine
$env:APP_ENV = "test"
$env:TEST_REDIS_URL = "redis://localhost:6381/15"
$env:JWT_SECRET_KEY = "ci-test-secret-key-com-pelo-menos-32-bytes"
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m pytest --cov=app --cov-report=xml --junitxml=.cache/junit.xml
.venv\Scripts\python.exe -m tests.support.verificar_ci .cache/junit.xml
docker stop viajajunto-redis-test
```

O PostgreSQL de testes usa porta 5433 e nome `viajajunto_test`. O pytest aplica as
migrações e recusa bancos sem sufixo `_test`; os cenários desfazem suas gravações.
As credenciais acima são exclusivas dos testes. Em Unix, use `.venv/bin/python`
e a sintaxe de exportação de variáveis do seu shell.

O CI executa Ruff, pytest/cobertura, auditoria de integrações, medição HTTP,
Spectral, SonarQube e build/scan Trivy. Os detalhes de reprodução, configuração de
secrets, limites da medição e publicação da imagem estão em
[validação e desempenho](docs/validacao-e-desempenho.md).

## Situação da entrega

A API fornece os dados para as telas; a validação das telas, acessibilidade,
responsividade e carregamento completo depende da integração com o frontend.
Chamadas do navegador em outra origem exigem CORS ou um proxy na mesma origem;
essa configuração ainda precisa ser definida e testada na topologia da entrega.
A exigência de hospedagem pública deve ser confirmada com o professor.

Os campos de imagem aceitam URLs, mas as fotos do seed ainda precisam ser
preenchidas. Entrega de emails externos depende de SMTP; o Compose usa Mailpit.
Reservas, pagamentos, divisão de custos, chat e edição simultânea em tempo real
estão fora do escopo original.

## Evidências e histórico

A [validação integrada](docs/validacao-e-desempenho.md) reúne o método de teste e
os resultados registrados. A [auditoria histórica](docs/historico/auditoria-final-requisitos.md)
compara os documentos originais com o estado do código naquele momento; suas
pendências devem ser lidas com as atualizações posteriores, não como contrato atual.
