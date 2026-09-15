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

docker-compose.yml    # Sobe o PostgreSQL em container
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
| ⏳ | Dockerfile da API / `docker compose up --build` completo |
| ⏳ | Hashing de senha |
| ⏳ | Testes automatizados |

A API já persiste usuários no PostgreSQL via `SQLAlchemyUsuarioRepository`
(`UsuarioRepositoryMemory` continua no projeto como adapter alternativo, útil para testes).
A tabela `usuarios` é criada e populada com um usuário inicial via Alembic
(ver seção [Migrations](#migrations-alembic)).

## Como rodar

### 1. Banco de dados (PostgreSQL via Docker)

```bash
cp .env.example .env
docker compose up -d      # sobe o Postgres em background
docker compose ps         # confirma que está "healthy"
```

### 2. API (rodando localmente, fora do Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

alembic upgrade head      # cria a tabela usuarios e insere o usuário inicial
uvicorn app.main:app --reload
```

A documentação interativa fica disponível em `http://localhost:8000/docs`.

### Parar o banco

```bash
docker compose down       # derruba o container, mantém os dados no volume
docker compose down -v    # derruba e apaga os dados (cuidado)
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

## Próximos passos

1. ~~Criar o modelo de persistência de `Usuario` em SQLAlchemy~~
2. ~~Implementar `SQLAlchemyUsuarioRepository` e trocar o adapter usado pela API~~
3. ~~Adicionar Alembic e a migration inicial da tabela de usuários~~
4. Dockerizar a API (Dockerfile + serviço no `docker-compose.yml`)
5. Tratar senha corretamente (port de hashing + adapter concreto)
6. Adicionar testes unitários (repository em memória) e de integração (API + persistência)
