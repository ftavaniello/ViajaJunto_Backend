# ViajaJunto — Backend

O ViajaJunto é uma aplicação web de planejamento colaborativo de viagens, desenvolvida para a disciplina de Construção de Software. Sua proposta é centralizar informações que normalmente ficam espalhadas entre conversas, planilhas, emails e anotações, permitindo que um grupo organize o roteiro em um ambiente compartilhado.

A plataforma foi especificada para reunir viagens com múltiplos destinos, datas, atividades e orçamento, além de visualização geográfica e descoberta de locais e atividades com avaliações da comunidade. A colaboração é o eixo do produto: o criador de uma viagem pode convidar outros usuários e definir quem pode editar ou apenas consultar o planejamento.

Este repositório contém a API do projeto. Atualmente, o backend implementa o módulo de usuários: cadastro, autenticação e gerenciamento da própria conta. As funcionalidades de planejamento de viagens fazem parte da evolução prevista e ainda não estão implementadas.

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
| `domain` | Define a entidade `Usuario` e os contratos `UsuarioRepository`, `PasswordHasher` e `TokenService` |
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
| SQLAlchemy e PostgreSQL | Mapeamento e armazenamento relacional dos usuários |
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

A entidade `Usuario` representa a conta e contém `id`, `nome`, `email` e `senha_hash`. Ela rejeita nome, email e hash vazios. A validação do formato do email e dos contratos HTTP fica nos schemas Pydantic; a verificação de email duplicado ocorre nos casos de uso de cadastro e atualização.

Na persistência, a tabela `usuarios` possui identificador inteiro gerado automaticamente e uma restrição de unicidade para o email. A API utiliza `SQLAlchemyUsuarioRepository`; a implementação `UsuarioRepositoryMemory` está disponível como alternativa para testes.

As migrações em `alembic/versions/` criam a tabela, inserem um usuário de exemplo e atualizam a senha desse registro para um hash bcrypt. No ambiente Docker Compose, as migrações pendentes são aplicadas antes da inicialização da API. Os dados do PostgreSQL são mantidos em um volume Docker.

O modelo oficial prevê também `viagem`, `membro_viagem`, `destino_catalogo`, `destino_viagem`, `catalogo_atividade`, `atividade_viagem`, `orcamento` e `avaliacao`. Ele distingue os dados reutilizáveis do catálogo das informações de cada viagem: por exemplo, a atividade do catálogo descreve um local ou experiência, enquanto sua associação à viagem registra horário, custo previsto e status. Cada viagem possui um orçamento, e as avaliações se vinculam às atividades do catálogo.

Essas entidades ainda não possuem implementação ou migrações neste backend. Mesmo o usuário tem uma diferença em relação ao modelo especificado: a tabela atual se chama `usuarios` e ainda não possui o campo `criado_em` previsto no documento.

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
tests/
├── domain/               # Validações da entidade Usuario
├── application/          # Casos de uso com repositório em memória
└── integration/          # API e persistência com PostgreSQL
```

## Execução local

Com Docker e Docker Compose disponíveis, crie um arquivo `.env` a partir de `.env.example` e execute, na raiz deste repositório:

```sh
docker compose up -d --build
```

O Compose inicia o PostgreSQL, aguarda o banco ficar saudável, aplica as migrações e disponibiliza a API na porta `8000`. O ambiente utiliza recarga automática ao editar os arquivos da aplicação.

A configuração da API utiliza `DATABASE_URL`, `JWT_SECRET_KEY` e `JWT_EXPIRE_MINUTES`. O Compose fornece `DATABASE_URL` diretamente ao container da API. Na configuração atual, as variáveis JWT do `.env` não são repassadas ao container, que usa os valores padrão; para personalizá-las nesse modo de execução, é necessário incluí-las no ambiente do serviço `api`. A chave padrão é destinada ao desenvolvimento local.

## Testes

A suíte contempla validações da entidade, regras dos casos de uso, autenticação, gerenciamento de conta e persistência. Os testes de domínio e aplicação usam o repositório em memória; os testes de integração dependem de PostgreSQL acessível e do schema criado pelas migrações.

Com as dependências instaladas no ambiente Python, a suíte pode ser executada com `pytest`. Para executar somente os testes sem banco:

```sh
pytest tests/domain tests/application
```

Quando o banco está indisponível, os testes de integração são marcados como ignorados (`skip`). Portanto, uma execução sem falhas nessas condições não comprova a integração com PostgreSQL.

## Validação do contrato OpenAPI

O workflow `.github/workflows/spectral.yml` executa em pushes e pull requests para
`main`. Ele exporta o contrato diretamente de `app.openapi()` e o valida com
`stoplightio/spectral-action`, usando o arquivo `.spectral.yaml`, que estende
`spectral:oas`. A exportação não precisa iniciar o servidor nem conectar ao banco.

Erros de validação fazem o check **Spectral** falhar. Os avisos seguem as
severidades padrão do conjunto de regras. Depois da primeira execução no GitHub,
adicione **Spectral** aos checks obrigatórios na regra de proteção da `main`.

O Spectral CLI também executa a validação para garantir a falha do job mesmo se
a action não conseguir publicar suas anotações no GitHub. Em PRs de forks,
somente o CLI executa, pois o token desses PRs não permite escrever checks.

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

Na validação local de 01/10/2026, a imagem passou nos 34 testes, nas migrações e
na inicialização do Uvicorn com resposta HTTP 200 em `/health`. O Trivy 0.75.0
não encontrou HIGH ou CRITICAL na imagem Alpine com a base de vulnerabilidades
utilizada nessa execução. Novos builds devem repetir o scan: esse resultado
não garante ausência de vulnerabilidades futuras ou de outras severidades.

O workflow `.github/workflows/ci.yml` constrói a imagem Docker e executa o Trivy
em pushes e pull requests para `main` e `develop`. O check `build-and-scan`
falha quando encontra vulnerabilidades HIGH ou CRITICAL nos pacotes do sistema
operacional ou nas dependências da aplicação, inclusive sem correção disponível.
Vulnerabilidades sem correção não são ignoradas para fazer o CI passar.

Inclua `build-and-scan` nos checks obrigatórios da proteção da `main`.
Esse workflow constrói e verifica a imagem; a publicação no Docker Hub é uma
etapa separada, ainda não configurada.

## Escopo e evolução

O módulo de usuários estabelece a base de autenticação, persistência e organização arquitetural do ViajaJunto. A evolução prevista contempla os módulos descritos nos requisitos, incluindo autorização por viagem e as integrações de catálogo e mapas previstas na arquitetura.

Este repositório contém apenas o backend. A interface web e os recursos de colaboração no planejamento de viagens ainda não estão presentes nesta implementação.

Estão fora do escopo da versão especificada: reservas de hotéis, voos e ingressos por APIs externas; chat em tempo real; aplicativo mobile nativo; pagamentos e divisão de custos; edição simultânea em tempo real; e gamificação de avaliações. A integração de catálogo com Google Places prevista na arquitetura não corresponde a uma integração de reservas.

## Referências de especificação

Esta descrição considera os documentos oficiais fornecidos pela equipe: `index.md` (visão geral), `requirements.md` (requisitos e regras de negócio) e `architecture.md` (arquitetura e modelo de dados). Os documentos de requisitos e arquitetura identificam a revisão inicial como versão 0.1, de 25/08/2026. Esses arquivos foram consultados externamente e não estão incluídos neste repositório.

Além da divergência de stack, há pontos que precisam de alinhamento entre os documentos: a visão geral e algumas regras mencionam avaliações de destinos, enquanto RF22–RF24 e o modelo relacional descrevem avaliações de atividades; o identificador de viagem é descrito como string/código de convite, mas as chaves estrangeiras correspondentes aparecem como inteiros. Este README registra essas diferenças sem definir uma solução que ainda não foi formalizada pela equipe.
