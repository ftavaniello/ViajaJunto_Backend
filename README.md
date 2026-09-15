# ViajaJunto — Backend

Boilerplate do backend do ViajaJunto, aplicação web de planejamento colaborativo de viagens.
Esta entrega tem como objetivo comprovar a stack e a arquitetura escolhidas usando `Usuario`
como um slice mínimo, porém real, do sistema.

## Stack

| Tecnologia | Papel no projeto |
|---|---|
| Python | Linguagem do backend |
| FastAPI | API HTTP e adapter de entrada |
| Pydantic | Validação dos contratos HTTP |
| SQLAlchemy | ORM e adapter de persistência |
| PostgreSQL | Banco de dados relacional |
| Docker / Compose | Ambiente reproduzível para o banco de dados |

## Arquitetura Hexagonal

O projeto segue a Arquitetura Hexagonal (Ports and Adapters): o domínio e os casos de uso ficam
no núcleo, sem depender de FastAPI, Pydantic ou SQLAlchemy. As tecnologias externas ficam nas
bordas, implementando os contratos (`ports`) definidos pelo núcleo.

```
HTTP -> FastAPI (Inbound Adapter)
        -> CriarUsuario (Application / Use Case)
           -> Usuario (Domain)
              -> UsuarioRepository (Port)
                 <- SQLAlchemyUsuarioRepository (Outbound Adapter, em uso atualmente)
                    -> PostgreSQL
                 <- UsuarioRepositoryMemory (Outbound Adapter, alternativo/testes)
```

## Estrutura de pastas

```
app/
├── domain/
│   ├── entities/
│   │   └── usuario.py              # Entidade Usuario, sem dependência de frameworks
│   └── ports/
│       └── usuario_repository.py   # Contrato de persistência (port)
├── application/
│   └── use_cases/
│       └── criar_usuario.py        # Regra de aplicação: criar usuário, validando email duplicado
├── adapters/
│   ├── inbound/
│   │   └── api/
│   │       ├── routes/
│   │       │   ├── health.py       # GET /health
│   │       │   └── usuario.py      # POST /usuarios
│   │       └── schemas/
│   │           └── usuario_schema.py
│   └── outbound/
│       └── persistence/
│           ├── usuario_model.py               # Modelo SQLAlchemy da tabela `usuarios`
│           ├── usuario_repository_sqlalchemy.py  # Adapter real, usado hoje pela API
│           └── usuario_repository_memory.py   # Adapter em memória (alternativo/testes)
├── infrastructure/
│   ├── config.py                   # Lê DATABASE_URL do .env
│   └── database.py                 # Engine e SessionLocal do SQLAlchemy
└── main.py

alembic/
├── versions/
│   ├── ..._cria_tabela_usuarios.py # Migration inicial (schema)
│   └── ..._seed_usuario_inicial.py # Migration de dado: insere 1 usuário inicial
└── env.py                          # Usa Base.metadata e DATABASE_URL do projeto

tests/
├── conftest.py                     # Fixtures: db_session (real Postgres) e email_teste
├── domain/
│   └── test_usuario.py             # Validações da entidade Usuario
├── application/
│   └── test_criar_usuario.py       # CriarUsuario + UsuarioRepositoryMemory (sem banco)
└── integration/
    ├── test_usuario_repository_sqlalchemy.py  # SQLAlchemyUsuarioRepository + Postgres real
    └── test_usuario_api.py                    # POST /usuarios via FastAPI TestClient + Postgres real

docker-compose.yml    # Sobe PostgreSQL (db) e a API (api) em containers
Dockerfile             # Imagem da API
pytest.ini              # Config do pytest (pythonpath)
.env.example           # Modelo das variáveis de ambiente
requirements.txt
```

## Status atual

| Status | Item |
|---|---|
| ✅ | FastAPI + Uvicorn executando |
| ✅ | GET /health |
| ✅ | Estrutura domain/application/adapters/infrastructure |
| ✅ | Entidade `Usuario` |
| ✅ | Port `UsuarioRepository` |
| ✅ | Use case `CriarUsuario` |
| ✅ | `UsuarioRepositoryMemory` (adapter de saída em memória) |
| ✅ | `POST /usuarios` via FastAPI |
| ✅ | PostgreSQL configurado via Docker Compose (`docker-compose.yml`, `config.py`, `database.py`) |
| ✅ | `UsuarioModel` (modelo SQLAlchemy da tabela `usuarios`) |
| ✅ | `SQLAlchemyUsuarioRepository` — API agora persiste usuários no PostgreSQL |
| ✅ | Alembic (migrations) — tabela `usuarios` + seed de um usuário inicial |
| ✅ | Dockerfile da API / `docker compose up --build` completo |
| ⏳ | Hashing de senha |
| ✅ | Testes automatizados (unitários e de integração) |

A API já persiste usuários no PostgreSQL via `SQLAlchemyUsuarioRepository`
(`UsuarioRepositoryMemory` continua no projeto como adapter alternativo, útil para testes).
A tabela `usuarios` é criada e populada com um usuário inicial via Alembic
(ver seção [Migrations](#migrations-alembic)).

## Como rodar

### Opção A — tudo via Docker (recomendado)

Dois containers: `db` (PostgreSQL) e `api` (FastAPI). A `api` espera o `db` ficar
saudável, roda `alembic upgrade head` automaticamente e sobe com `--reload`
(o código de `app/` e `alembic/` é montado como volume, então editar localmente
já reflete no container, sem rebuild).

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps         # confirma que os dois estão "healthy"/"running"
```

A documentação interativa fica em `http://localhost:8000/docs`.

```bash
docker compose down       # derruba os containers, mantém os dados no volume
docker compose down -v    # derruba e apaga os dados (cuidado)
```

### Opção B — API local (fora do Docker), banco via Docker

Útil para debugar/rodar a API diretamente na sua IDE.

```bash
cp .env.example .env
docker compose up -d db   # sobe só o Postgres

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

alembic upgrade head      # cria a tabela usuarios e insere o usuário inicial
uvicorn app.main:app --reload
```

## Migrations (Alembic)

O schema do banco é versionado com Alembic (`alembic/versions/`). `env.py` usa o
`DATABASE_URL` de `config.py` e o `Base.metadata` de `database.py`, então não é preciso
configurar nada além do `.env` para rodar.

```bash
alembic upgrade head                              # aplica todas as migrations pendentes
alembic revision --autogenerate -m "mensagem"     # gera uma nova migration a partir de mudanças nos models
alembic downgrade -1                              # desfaz a última migration
```

A migration inicial (`..._cria_tabela_usuarios.py`) cria a tabela `usuarios`. A segunda
(`..._seed_usuario_inicial.py`) insere um usuário de exemplo (`usuario@viajajunto.com`)
para facilitar testes manuais — a senha ainda é salva em texto puro, já que o hashing
(passo 5 do roadmap) ainda não foi implementado.

## Testes

```bash
pip install -r requirements.txt   # já inclui pytest e httpx2
pytest                             # roda toda a suíte
pytest tests/domain tests/application   # só os testes unitários, sem precisar de banco
```

- `tests/domain` e `tests/application` são testes unitários puros (entidade `Usuario` e o
  use case `CriarUsuario` com `UsuarioRepositoryMemory`) — não dependem de banco de dados
  e mostram a vantagem da arquitetura hexagonal: o núcleo é testável sem subir nada externo.
- `tests/integration` valida `SQLAlchemyUsuarioRepository` e o endpoint `POST /usuarios`
  contra um PostgreSQL real. Precisa do banco rodando (`docker compose up -d db`); se não
  estiver acessível, esses testes são pulados automaticamente (`pytest.skip`) em vez de falhar.
- Os testes de integração usam emails únicos com prefixo `teste-` e o `conftest.py` apaga
  esses registros ao final de cada teste, então não sujam o banco de desenvolvimento.

## Próximos passos

1. ~~Criar o modelo de persistência de `Usuario` em SQLAlchemy~~
2. ~~Implementar `SQLAlchemyUsuarioRepository` e trocar o adapter usado pela API~~
3. ~~Adicionar Alembic e a migration inicial da tabela de usuários~~
4. ~~Dockerizar a API (Dockerfile + serviço no `docker-compose.yml`)~~
5. Tratar senha corretamente (port de hashing + adapter concreto)
6. ~~Adicionar testes unitários (repository em memória) e de integração (API + persistência)~~
