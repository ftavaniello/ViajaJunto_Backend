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
                 <- UsuarioRepositoryMemory (Outbound Adapter, em uso atualmente)
                 <- SQLAlchemyUsuarioRepository (Outbound Adapter, ainda não implementado)
                    -> PostgreSQL
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
│           └── usuario_repository_memory.py  # Adapter em memória (usado hoje pela API)
├── infrastructure/
│   ├── config.py                   # Lê DATABASE_URL do .env
│   └── database.py                 # Engine e SessionLocal do SQLAlchemy
└── main.py

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
| ⏳ | `SQLAlchemyUsuarioRepository` — persistência real ainda não implementada |
| ⏳ | Alembic (migrations) |
| ⏳ | Dockerfile da API / `docker compose up --build` completo |
| ⏳ | Hashing de senha |
| ⏳ | Testes automatizados |

A API atualmente persiste usuários em memória (`UsuarioRepositoryMemory`); os dados do
PostgreSQL subido via Docker ainda não são usados pelo fluxo de `POST /usuarios`.

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

uvicorn app.main:app --reload
```

A documentação interativa fica disponível em `http://localhost:8000/docs`.

### Parar o banco

```bash
docker compose down       # derruba o container, mantém os dados no volume
docker compose down -v    # derruba e apaga os dados (cuidado)
```

## Próximos passos

1. Criar o modelo de persistência de `Usuario` em SQLAlchemy
2. Implementar `SQLAlchemyUsuarioRepository` e trocar o adapter usado pela API
3. Adicionar Alembic e a migration inicial da tabela de usuários
4. Dockerizar a API (Dockerfile + serviço no `docker-compose.yml`)
5. Tratar senha corretamente (port de hashing + adapter concreto)
6. Adicionar testes unitários (repository em memória) e de integração (API + persistência)
