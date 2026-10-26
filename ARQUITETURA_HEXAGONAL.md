# ViajaJunto — Regras obrigatórias de Arquitetura Hexagonal

> **Status:** norma de implementação do backend. Leia antes de criar, modificar ou revisar qualquer funcionalidade.
> **Stack:** Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Alembic e pytest.
> **Princípio central:** o núcleo de negócio não depende de frameworks, banco de dados, HTTP ou serviços externos.

## 1. Direção das dependências (regra inegociável)

```text
HTTP / FastAPI (adapter de entrada)
            |
            v
Application (casos de uso) ---> Domain (entidades e regras)
            |                       ^
            v                       |
Portas abstratas (contratos) <--- implementadas por adapters de saída
                                      |
                                      v
                           SQLAlchemy / PostgreSQL / APIs
```

- `domain` **não importa** `application`, `adapters`, `infrastructure`, FastAPI, Pydantic HTTP, SQLAlchemy ou drivers de banco.
- `application` depende de `domain` e de **interfaces/ports**, nunca de adapters concretos, FastAPI ou SQLAlchemy.
- `adapters/inbound` traduz protocolos externos para chamadas de casos de uso.
- `adapters/outbound` implementa portas e traduz dados para mecanismos externos.
- `infrastructure` configura tecnologias, sessões, ambiente e composição das dependências; não contém regras de negócio.
- Uma dependência apontando do núcleo para um detalhe externo é uma **violação arquitetural**, mesmo que o código funcione.

## 2. Responsabilidades por camada

### `app/domain/`

**Pode conter:** entidades, value objects, invariantes, regras puras, exceções de domínio e contratos (`ports`) quando esta for a convenção do projeto.

**Não pode conter:** `APIRouter`, `HTTPException`, `BaseModel` de request/response, `Session`, `Column`, `Mapped`, consultas SQL, `os.getenv`, chamadas HTTP, JWT ou dependências de infraestrutura.

A entidade `Usuario` representa comportamento e estado de negócio, não uma tabela SQLAlchemy nem um schema Pydantic de entrada.

### `app/application/`

**Pode conter:** casos de uso como `CriarUsuario`, coordenação de regras, transações abstratas quando necessárias, dependência de portas, DTOs de aplicação independentes de HTTP.

**Não pode conter:** `Depends`, `HTTPException`, `APIRouter`, `Session`, `select()` SQLAlchemy, SQL bruto, criação de engine ou instanciação de `SQLAlchemyUsuarioRepository`.

Cada caso de uso deve ser invocável por teste Python sem iniciar servidor, banco ou Docker.

### `app/domain/ports/`

As portas descrevem **capacidades exigidas pelo núcleo**, não detalhes da tecnologia. Exemplo: `UsuarioRepository.buscar_por_email(email)`; evite `executar_query_sql()` ou `obter_session()`.

- Use `ABC` ou `Protocol` de Python; mantenha assinaturas tipadas.
- Interfaces retornam entidades/DTOs de domínio ou aplicação, **não** models SQLAlchemy.
- Crie uma porta apenas quando houver uma fronteira real com algo externo; não crie abstrações sem necessidade.
- Portas de hashing, relógio, envio de mensagens ou geolocalização podem surgir quando os casos de uso realmente precisarem dessas capacidades.

### `app/adapters/inbound/api/`

Rotas FastAPI devem somente: receber entrada, validar formato via Pydantic, obter autenticação/contexto, chamar caso de uso, mapear resultados/erros para HTTP e devolver schema de resposta.

**Não podem:** conter consultas SQL, instanciar engine, executar regras centrais de negócio ou acessar repositórios diretamente para contornar o caso de uso.

### `app/adapters/outbound/`

Implementações concretas de portas: `SQLAlchemyUsuarioRepository`, `UsuarioRepositoryMemory`, cliente de mapas, serviço de hashing etc.

- Fazem conversão entre `UsuarioModel` (ORM) e `Usuario` (domínio).
- Nunca retornam objetos ORM ao núcleo.
- Não importam routers HTTP.
- Não decidem políticas de negócio que pertencem ao domínio/caso de uso.

### `app/infrastructure/`

Configurações, conexão e sessão do banco, carregamento de ambiente e montagem das dependências. Pode conhecer adapters concretos para injetá-los nos casos de uso. Não deve concentrar lógica de negócio.

## 3. Estrutura de referência

```text
app/
  domain/
    entities/usuario.py
    ports/usuario_repository.py
  application/
    use_cases/criar_usuario.py
  adapters/
    inbound/api/routes/usuario.py
    inbound/api/schemas/usuario_schema.py
    outbound/persistence/usuario_model.py
    outbound/persistence/usuario_repository_sqlalchemy.py
    outbound/persistence/usuario_repository_memory.py
  infrastructure/
    config.py
    database.py
    dependencies.py             # composição/injeção; criar quando necessário
  main.py
alembic/
tests/
  domain/
  application/
  integration/
```

A estrutura é uma referência, não licença para criar arquivos vazios. Preserve convenções existentes quando compatíveis com as regras.

## 4. Fluxo obrigatório de uma funcionalidade

1. Identificar regras, invariantes e permissões do negócio.
2. Implementar ou ajustar entidade/value object no domínio, quando necessário.
3. Definir/ajustar portas exigidas por dependências externas.
4. Implementar caso de uso em `application` usando somente abstrações.
5. Implementar adapter de saída, incluindo mapeamento ORM ↔ domínio.
6. Configurar injeção de dependências na borda da aplicação.
7. Criar/ajustar schemas e rotas FastAPI, mantendo rotas finas.
8. Criar migration Alembic se o modelo persistido mudou.
9. Adicionar testes unitários do núcleo e de integração das bordas.
10. Atualizar contrato OpenAPI, documentação e exemplos quando a API mudar.

Não comece colocando a regra de negócio dentro de uma rota ou model ORM.

## 5. Exemplo de dependência correta

```python
# application/use_cases/criar_usuario.py
from app.domain.ports.usuario_repository import UsuarioRepository

class CriarUsuario:
    def __init__(self, repository: UsuarioRepository):
        self.repository = repository

    def execute(self, ...):
        # regras de aplicação; sem FastAPI ou SQLAlchemy
        ...
```

```python
# adapters/outbound/persistence/usuario_repository_sqlalchemy.py
from app.domain.ports.usuario_repository import UsuarioRepository

class SQLAlchemyUsuarioRepository(UsuarioRepository):
    # implementação concreta, isolada na borda
    ...
```

```python
# infrastructure/dependencies.py (exemplo conceitual)
# A composição pode importar adapter concreto e injetá-lo no caso de uso.
# Não fazer essa importação dentro de application/use_cases/.
```

## 6. Regras de persistência e transações

- `Usuario` e `UsuarioModel` são objetos distintos com responsabilidades distintas.
- Repositórios fazem persistência e mapeamento, sem expor `Session` ao caso de uso.
- Sessões têm ciclo de vida controlado na infraestrutura, preferencialmente por requisição.
- Limites de transação devem ser explícitos; em casos de uso com múltiplos repositórios, considerar uma abstração de unidade de trabalho em vez de commits arbitrários em cada operação.
- Restrições de integridade, como unicidade de email, também devem existir no banco; verificar previamente no caso de uso não elimina condições de corrida.
- Alterações de schema usam Alembic; não depender de `create_all()` como mecanismo de evolução de produção.
- `DATABASE_URL` e credenciais vêm de variáveis de ambiente; nunca versionar segredos.

## 7. Autenticação, autorização e segurança

- Senhas em texto puro nunca são persistidas, logadas ou devolvidas em responses.
- O caso de uso depende de uma porta de hashing/verificação quando necessário; o algoritmo concreto fica no adapter.
- Validação criptográfica do JWT ocorre na borda; o núcleo recebe identidade/contexto autenticado em tipos independentes de HTTP.
- Permissões de viagem (`criador`, `EDITOR`, `VISUALIZADOR`) são regras de aplicação/domínio e **não** devem depender apenas de validação na rota.
- Erros de domínio/aplicação não devem importar `HTTPException`; o adapter HTTP converte erros em `400`, `401`, `403`, `404`, `409`, `422` conforme o contrato.
- Nunca confiar em `usuario_id` fornecido pelo cliente como prova de identidade.

## 8. Testes obrigatórios

- **Domínio:** invariantes e regras sem banco, HTTP ou mocks de frameworks.
- **Aplicação:** casos de uso testados com fakes/memory adapters ou mocks das portas, incluindo cenários de falha.
- **Integração:** repositório SQLAlchemy com PostgreSQL e API com dependências reais/controladas.
- **Contrato:** rotas, autenticação, status HTTP e payloads devem corresponder ao OpenAPI documentado.
- O núcleo deve continuar testável sem `docker compose up`.
- A pipeline deve executar lint, testes/cobertura, Spectral, SonarQube e Trivy conforme os requisitos do T2.

## 9. Anti-patterns proibidos

- Importar `Session`, `select`, `HTTPException` ou `Depends` em `domain`/`application`.
- Colocar regras de autorização apenas em decorators/routers.
- Usar um model SQLAlchemy como entidade de domínio.
- Retornar um ORM model diretamente de um caso de uso.
- Instanciar `SQLAlchemyUsuarioRepository` dentro de `CriarUsuario`.
- Chamar APIs externas diretamente de uma entidade ou caso de uso sem porta.
- Usar estado global mutável de repositório em produção.
- Criar uma interface genérica para cada classe sem justificativa de fronteira.
- Misturar DTO HTTP, entidade de domínio e model ORM em uma classe única.
- Mudar o contrato OpenAPI sem alinhar implementação e testes (ou vice-versa).

## 10. Checklist obrigatório do Codex antes de concluir uma mudança

- [ ] Li este documento antes de implementar.
- [ ] Identifiquei claramente quais arquivos pertencem a cada camada.
- [ ] Nenhuma dependência aponta do núcleo para frameworks ou adapters.
- [ ] Regras de negócio estão no domínio/caso de uso, não na rota nem no ORM.
- [ ] Portas representam capacidades do negócio e não APIs de bibliotecas.
- [ ] Adapters concretos implementam portas e fazem conversões necessárias.
- [ ] Dependências concretas são montadas na borda, não no núcleo.
- [ ] Entidades/DTOs do núcleo não expõem `Session` nem models ORM.
- [ ] Autenticação/autorização e tratamento de erros respeitam as fronteiras.
- [ ] Adicionei/atualizei testes unitários e de integração adequados.
- [ ] Atualizei Alembic e OpenAPI quando necessário.
- [ ] Executei verificações disponíveis e relatei as que não consegui executar.

## 11. Instrução operacional para agentes de código

**Antes de qualquer implementação:** leia este documento e inspecione os arquivos envolvidos. Faça um plano curto indicando camada, portas, adapters, testes e alterações no contrato. Se encontrar código existente em desacordo com a arquitetura, sinalize explicitamente; não replique o desvio. Corrija violações dentro do escopo da tarefa ou proponha uma refatoração separada. Não afirme conformidade sem verificar imports e fluxo de dependências. Se houver conflito entre convenção existente e estas regras, priorize estas regras e explique o impacto.

**Antes de encerrar:** apresente um resumo dos arquivos alterados, como as dependências respeitam a arquitetura, quais testes/linters foram executados e pendências reais.
