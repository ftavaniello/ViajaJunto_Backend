# ViajaJunto — Backend

O ViajaJunto é uma aplicação web de planejamento colaborativo de viagens, desenvolvida para a disciplina de Construção de Software. Sua proposta é centralizar informações que normalmente ficam espalhadas entre conversas, planilhas, emails e anotações, permitindo que um grupo organize o roteiro em um ambiente compartilhado.

A plataforma foi especificada para reunir viagens com múltiplos destinos, datas, atividades e orçamento, além de visualização geográfica e descoberta de locais e atividades com avaliações da comunidade. A colaboração é o eixo do produto: o criador de uma viagem pode convidar outros usuários e definir quem pode editar ou apenas consultar o planejamento.

Este repositório contém a API do projeto. Atualmente, o backend implementa o módulo de usuários: cadastro, autenticação e gerenciamento da própria conta. As funcionalidades de planejamento de viagens fazem parte da evolução prevista e ainda não estão implementadas; o esquema do banco para elas, porém, já foi definido e criado (ver [Dados e persistência](#dados-e-persistência)).

## Visão do produto

No fluxo previsto, um usuário cria uma viagem com nome, descrição e datas gerais, organiza os destinos na ordem de visita e associa atividades a cada parada. As atividades incluem informações como horário, duração, categoria e custo previsto. O orçamento reúne esses custos para apresentar o total planejado, o saldo disponível e a distribuição por categoria.

O criador compartilha a viagem por código de convite e administra os colaboradores. As permissões são específicas de cada viagem:

| Perfil | Participação prevista |
|---|---|
| Visitante | Consulta o catálogo público e as avaliações, sem criar viagens ou publicar avaliações |
| Usuário registrado | Cria viagens, gerencia seu planejamento e publica avaliações |
| Criador da viagem | Convida colaboradores, altera permissões e remove membros |
| Colaborador Editor | Adiciona, edita e remove destinos, atividades e informações de orçamento |
| Colaborador Visualizador | Consulta o planejamento com acesso somente leitura |

O acesso aos dados de uma viagem deve ser restrito ao criador e aos colaboradores convidados. Os recursos públicos de catálogo e avaliações constituem um acesso separado do planejamento privado.

A matriz detalhada de permissões (quem edita dados gerais e status, quem exclui a viagem, quem avalia), as regras de convite e as demais decisões de produto estão em [`docs/decisoes-de-produto.md`](docs/decisoes-de-produto.md).

## Escopo especificado e implementação atual

| Área | Previsão nos requisitos | Situação neste backend |
|---|---|---|
| Autenticação e perfil — RF01–RF03 | Cadastro, login, logout e recuperação de senha por email | Cadastro e login implementados, além de consulta, edição, troca de senha e exclusão da conta; não há endpoint de logout/revogação nem recuperação por email |
| Viagens — RF04–RF07 | Criação, edição, exclusão, painel pessoal e status de planejamento | Ainda não implementado |
| Destinos — RF08–RF11 | Múltiplos destinos ordenados, informações da estadia, pesquisa e mapa de países visitados | Ainda não implementado |
| Atividades — RF12–RF14 | Atividades por destino, horários, duração, custos e status | Ainda não implementado |
| Orçamento — RF15–RF17 | Limite total, custos previstos e resumo financeiro por categoria | Ainda não implementado |
| Colaboração — RF18–RF21 | Convite por código, permissões de Editor/Visualizador e notificações in-app | Ainda não implementado |
| Avaliação e descoberta — RF22–RF25 | Avaliações, páginas públicas, catálogo com filtros e destaques | Ainda não implementado |

Nas áreas marcadas como "Ainda não implementado", o que existe hoje é apenas o esquema do banco (tabelas e migração), sem casos de uso, rotas ou repositórios.

A especificação também estabelece interface responsiva e acessível, carregamento das páginas principais em menos de três segundos em condições normais, autenticação por token, senhas com hash e separação entre frontend e backend. Esses são requisitos do produto; este README não representa uma validação de atendimento a todos eles.

## Funcionamento da aplicação

O acesso começa pelo cadastro de uma conta com nome, email e senha. A API valida os dados recebidos, verifica se o email já está cadastrado e transforma a senha em um hash bcrypt antes de salvar o usuário no PostgreSQL. As respostas de usuário contêm apenas identificador, nome e email.

No login, o backend confere as credenciais e emite um token JWT com o identificador do usuário e um prazo de expiração. Esse token acompanha as próximas requisições no cabeçalho `Authorization: Bearer <token>`.

As operações de conta usam a rota `/usuarios/me`: o usuário é identificado pelo token, sem precisar informar um identificador na URL. A cada acesso protegido, a API valida o token e consulta se a conta ainda existe no banco.

O usuário autenticado pode consultar seu perfil, alterar nome e email, trocar a senha mediante confirmação da senha atual e excluir sua conta. Após a exclusão, o token deixa de permitir acesso às rotas protegidas, pois a conta não é mais encontrada.

## Funcionalidades disponíveis

| Funcionalidade | Comportamento |
|---|---|
| Cadastro | Cria uma conta com email único e senha de pelo menos oito caracteres no contrato da API |
| Autenticação | Valida email e senha e retorna um token JWT |
| Consulta de perfil | Retorna os dados da própria conta |
| Atualização de perfil | Altera nome e/ou email; campos omitidos ou nulos permanecem inalterados |
| Alteração de senha | Exige a senha atual e uma nova senha de pelo menos oito caracteres |
| Exclusão de conta | Remove permanentemente o usuário autenticado |
| Verificação de disponibilidade | Expõe uma rota pública de liveness da API |

## Arquitetura

A documentação oficial descreve uma arquitetura cliente-servidor com frontend separado, API REST, PostgreSQL e serviços externos de mapas e locais/atividades. Prevê um catálogo interno enriquecido com Google Places, preservando as avaliações próprias e os dados associados às viagens. Essas integrações ainda não existem neste repositório.

O documento de arquitetura menciona NextJS para o frontend e NestJS para o backend, embora sua tabela de restrições deixe linguagem e framework a definir. A implementação atual utiliza Python e FastAPI. A organização hexagonal descrita abaixo corresponde ao código presente; a divergência de stack permanece pendente de alinhamento na documentação oficial.

O backend segue a **Arquitetura Hexagonal (Ports and Adapters)**. As regras de domínio e os casos de uso ficam no núcleo da aplicação, enquanto HTTP, persistência e bibliotecas de segurança são integrados por adaptadores.

Essa separação permite exercitar os casos de uso com um repositório em memória e utilizar PostgreSQL na API, mantendo os mesmos contratos de persistência.

| Camada | Responsabilidade no projeto |
|---|---|
| `domain` | Define a entidade `Usuario`, os contratos `UsuarioRepository`, `PasswordHasher` e `TokenService`, o vocabulário fechado do domínio (`enums.py`: papéis, status, categorias, tipos de notificação) e as constantes das regras de negócio (`regras.py`) |
| `application` | Coordena os casos de uso de criação, autenticação, atualização, alteração de senha e exclusão de usuários |
| `adapters/inbound` | Recebe requisições HTTP, valida contratos com Pydantic e converte resultados em respostas da API |
| `adapters/outbound` | Implementa persistência com SQLAlchemy ou memória, hash com bcrypt e tokens com PyJWT |
| `infrastructure` | Centraliza configurações, conexão e sessões do banco de dados |

Em uma operação de cadastro, por exemplo, a rota recebe os dados e chama `CriarUsuario`. O caso de uso consulta o repositório para verificar duplicidade de email, solicita o hash da senha e salva a entidade. As implementações concretas de persistência e hashing são fornecidas ao caso de uso pela camada de entrada.

O domínio e os casos de uso não dependem de FastAPI, Pydantic ou SQLAlchemy. A montagem da aplicação e o registro das rotas ficam em `app/main.py`.

## Tecnologias

| Tecnologia | Papel |
|---|---|
| Python | Linguagem do backend; a imagem Docker utiliza Python 3.13 |
| FastAPI e Uvicorn | API HTTP e servidor da aplicação |
| Pydantic | Validação dos dados de entrada e definição dos contratos de resposta |
| SQLAlchemy e PostgreSQL | Mapeamento e armazenamento relacional dos dados |
| Alembic | Versionamento e aplicação de alterações no banco |
| bcrypt | Geração e verificação de hashes de senha |
| PyJWT | Emissão e validação de tokens JWT |
| Docker Compose | Execução da API e do PostgreSQL em containers |
| pytest | Testes automatizados de domínio, aplicação e integração |

## API HTTP

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| `GET` | `/health` | Público | Verifica se a API está respondendo |
| `POST` | `/usuarios` | Público | Cadastra um usuário |
| `POST` | `/auth/login` | Público | Autentica e retorna o token de acesso |
| `GET` | `/usuarios/me` | JWT | Consulta o perfil autenticado |
| `PATCH` | `/usuarios/me` | JWT | Atualiza nome e/ou email |
| `PATCH` | `/usuarios/me/senha` | JWT | Altera a senha da conta |
| `DELETE` | `/usuarios/me` | JWT | Exclui a conta autenticada |

Os contratos completos, exemplos e respostas estão disponíveis no Swagger UI em [http://localhost:8000/docs](http://localhost:8000/docs), com a aplicação em execução. O documento OpenAPI fica em `/openapi.json`.

A proteção das rotas de conta é feita pela dependência `get_usuario_atual`. Tokens ausentes, inválidos ou expirados e tokens de contas excluídas resultam em resposta `401`. O JWT utiliza o algoritmo HS256 e tem validade padrão de 60 minutos. A troca de senha não revoga tokens já emitidos; eles continuam sujeitos à expiração e à existência da conta.

## Dados e persistência

A entidade `Usuario` representa a conta e contém `id`, `nome`, `email`, `senha_hash` e `criado_em` (preenchido pelo banco na criação). Ela rejeita nome, email e hash vazios. A validação do formato do email e dos contratos HTTP fica nos schemas Pydantic; a verificação de email duplicado ocorre nos casos de uso de cadastro e atualização.

Na persistência, a tabela `usuarios` possui identificador inteiro gerado automaticamente, uma restrição de unicidade para o email e a data de criação (`criado_em`, `TIMESTAMPTZ`). A API utiliza `SQLAlchemyUsuarioRepository`; a implementação `UsuarioRepositoryMemory` está disponível como alternativa para testes.

As migrações em `alembic/versions/` criam a tabela de usuários, inserem um usuário de exemplo, atualizam a senha desse registro para um hash bcrypt e, por fim, criam o esquema de viagens descrito abaixo (migração `a3f1c9d27b45`). No ambiente Docker Compose, as migrações pendentes são aplicadas antes da inicialização da API. Os dados do PostgreSQL são mantidos em um volume Docker.

O modelo oficial prevê também `viagem`, `membro_viagem`, `destino_catalogo`, `destino_viagem`, `catalogo_atividade`, `atividade_viagem`, `orcamento` e `avaliacao`. Ele distingue os dados reutilizáveis do catálogo das informações de cada viagem: por exemplo, a atividade do catálogo descreve um local ou experiência, enquanto sua associação à viagem registra horário, custo previsto e status. Cada viagem possui um orçamento, e as avaliações se vinculam às atividades do catálogo.

Essas tabelas, mais `notificacoes` e `tokens_recuperacao_senha`, foram criadas pela migração `a3f1c9d27b45` conforme as decisões de [`docs/decisoes-de-produto.md`](docs/decisoes-de-produto.md): identificadores inteiros com o código de convite em coluna própria, avaliação de atividades com ranking de destinos derivado, papéis, validade de convites, datas, moeda e efeitos das exclusões. Por enquanto é apenas o esquema: não há casos de uso, rotas nem repositórios para elas. A tabela `usuarios` ganhou o campo `criado_em` previsto no documento; ela mantém o nome `usuarios` em vez de `usuario`.

## Organização do repositório

```text
app/
├── domain/
│   ├── entities/          # Entidades e validações de domínio
│   └── ports/             # Contratos de persistência e segurança
├── application/
│   └── use_cases/         # Operações da aplicação
├── adapters/
│   ├── inbound/api/       # Rotas, schemas HTTP e autenticação das requisições
│   └── outbound/          # Persistência e implementações de segurança
├── infrastructure/       # Configuração e acesso ao banco
└── main.py               # Criação da aplicação FastAPI
alembic/                  # Migrações do banco de dados
docs/                     # Decisões de produto e modelo de dados
tests/
├── domain/               # Validações da entidade Usuario
├── application/          # Casos de uso com repositório em memória
└── integration/          # API, persistência e modelo de dados com PostgreSQL
```

## Execução local

Com Docker e Docker Compose disponíveis, crie um arquivo `.env` a partir de `.env.example` e execute, na raiz deste repositório:

```sh
docker compose up -d --build
```

O Compose inicia o PostgreSQL, aguarda o banco ficar saudável, aplica as migrações e disponibiliza a API na porta `8000`. O ambiente utiliza recarga automática ao editar os arquivos da aplicação.

A configuração da API utiliza