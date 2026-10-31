# ViajaJunto — Backend

O ViajaJunto é uma aplicação web de planejamento colaborativo de viagens, desenvolvida para a disciplina de Construção de Software. Sua proposta é centralizar informações que normalmente ficam espalhadas entre conversas, planilhas, emails e anotações, permitindo que um grupo organize o roteiro em um ambiente compartilhado.

A plataforma foi especificada para reunir viagens com múltiplos destinos, datas, atividades e orçamento, além de visualização geográfica e descoberta de locais e atividades com avaliações da comunidade. A colaboração é o eixo do produto: o criador de uma viagem pode convidar outros usuários e definir quem pode editar ou apenas consultar o planejamento.

Este repositório contém a API do projeto. Atualmente, o backend implementa o módulo de usuários (cadastro, autenticação e gerenciamento da própria conta) e o cadastro de viagens com a política central de acesso por viagem. As demais funcionalidades de planejamento fazem parte da evolução prevista; o esquema do banco para elas, porém, já foi definido e criado (ver [Dados e persistência](#dados-e-persistência)).

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
| Autenticação e perfil — RF01–RF03 | Cadastro, login, logout e recuperação de senha por email | Cadastro, login, logout (com revogação do token no servidor) e recuperação de senha por email implementados, além de consulta, edição, troca de senha e exclusão da conta |
| Viagens — RF04–RF07 | Criação, edição, exclusão, painel pessoal e status de planejamento | Criação, consulta, listagem, edição, exclusão e status (RF04, RF05, RF07), com acesso restrito ao criador e colaboradores (RN06); listagem paginada para o painel pessoal (RF06), incluindo o papel do usuário |
| Destinos — RF08–RF11 | Múltiplos destinos ordenados, informações da estadia, pesquisa e mapa de países visitados | Catálogo público e destinos do roteiro com datas e ordem de visita (RF08–RF10); mapa de países visitados pendente |
| Atividades — RF12–RF14 | Atividades por destino, horários, duração, custos e status | Planejamento por parada, ordem cronológica, custos previstos e status implementados (#24) |
| Orçamento — RF15–RF17 | Limite total, custos previstos e resumo financeiro por categoria | Custos previstos por atividade implementados (RF16); limite e resumo financeiro pendentes (#25) |
| Colaboração — RF18–RF21 | Convite por código, permissões de Editor/Visualizador e notificações in-app | Ainda não implementado |
| Avaliação e descoberta — RF22–RF25 | Avaliações, páginas públicas, catálogo com filtros e destaques | Catálogo público, detalhe e filtros descritivos implementados (#20); avaliações, nota mínima e destaques pendentes |

Nas áreas marcadas como "Ainda não implementado", o que existe hoje é apenas o esquema do banco (tabelas e migração), sem casos de uso, rotas ou repositórios.

A especificação também estabelece interface responsiva e acessível, carregamento das páginas principais em menos de três segundos em condições normais, autenticação por token, senhas com hash e separação entre frontend e backend. Esses são requisitos do produto; este README não representa uma validação de atendimento a todos eles.

## Funcionamento da aplicação

O acesso começa pelo cadastro de uma conta com nome, email e senha. A API valida os dados recebidos, verifica se o email já está cadastrado e transforma a senha em um hash bcrypt antes de salvar o usuário no PostgreSQL. As respostas de usuário contêm apenas identificador, nome e email.

No login, o backend confere as credenciais e emite um token JWT com o identificador do usuário e um prazo de expiração. Esse token acompanha as próximas requisições no cabeçalho `Authorization: Bearer <token>`.

As operações de conta usam a rota `/usuarios/me`: o usuário é identificado pelo token, sem precisar informar um identificador na URL. A cada acesso protegido, a API valida o token e consulta se a conta ainda existe no banco.

O usuário autenticado pode consultar seu perfil, alterar nome e email, trocar a senha mediante confirmação da senha atual e excluir sua conta. Após a exclusão, o token deixa de permitir acesso às rotas protegidas, pois a conta não é mais encontrada.

No logout (`POST /auth/logout`), o servidor revoga o token enviado: ele e qualquer cópia dele deixam de funcionar imediatamente, enquanto outras sessões do usuário continuam válidas. A troca de senha encerra todas as sessões, inclusive a atual. A política completa está em [`docs/sessoes-e-logout.md`](docs/sessoes-e-logout.md).

Quem esqueceu a senha pede um link em `POST /auth/recuperar-senha`. A resposta é sempre a mesma, exista ou não a conta. O link chega por email, vale por 60 minutos e só pode ser usado uma vez; `POST /auth/redefinir-senha` troca a senha e encerra todas as sessões. No Docker Compose os emails ficam no Mailpit, em <http://localhost:8025>. Detalhes, configuração e passo a passo em [`docs/recuperacao-de-senha.md`](docs/recuperacao-de-senha.md).

## Funcionalidades disponíveis

| Funcionalidade | Comportamento |
|---|---|
| Cadastro | Cria uma conta com email único e senha de pelo menos oito caracteres no contrato da API |
| Autenticação | Valida email e senha e retorna um token JWT |
| Logout | Revoga no servidor o token usado; cópias dele também passam a receber 401 |
| Consulta de perfil | Retorna os dados da própria conta |
| Atualização de perfil | Altera nome e/ou email; campos omitidos ou nulos permanecem inalterados |
| Alteração de senha | Exige a senha atual e uma nova senha de pelo menos oito caracteres; encerra todas as sessões |
| Recuperação de senha | Envia por email um link de uso único, válido por 60 minutos, sem revelar se o email tem conta; a redefinição encerra todas as sessões |
| Exclusão de conta | Remove permanentemente o usuário autenticado |
| Verificação de disponibilidade | Expõe uma rota pública de liveness da API |

## Atividades do roteiro

As rotas autenticadas `/viagens/{viagem_id}/destinos/{destino_id}/atividades`
permitem planejar atividades do catálogo com data, horário, duração, custo e status.
Criador e Editor alteram; Visualizador consulta. A listagem é cronológica, com
atividades sem horário ao fim de cada dia. Veja [contrato e teste no Swagger](docs/atividades-roteiro.md).

## Destinos do roteiro

As rotas autenticadas `/viagens/{viagem_id}/destinos` permitem listar, consultar,
adicionar, editar, excluir e reordenar paradas. Criador e Editor alteram;
Visualizador consulta. Datas respeitam o período da viagem e os dados públicos
do catálogo são preservados. Excluir uma parada remove suas atividades.
Veja [contrato, regras e teste pelo Swagger](docs/destinos-roteiro.md).

## Catálogo público de destinos

`GET /catalogo/destinos` pesquisa por nome, país e categoria, com paginação;
`GET /catalogo/destinos/{destino_id}` consulta o detalhe. São consultas públicas,
sem dados privados de viagens. A carga é operacional e reutiliza o seed e importador
do catálogo. Veja [contrato e exemplos](docs/catalogo-destinos.md).

## Catálogo público de atividades

A issue #20 disponibiliza `GET /catalogo/atividades` e
`GET /catalogo/atividades/{atividade_id}`, sem autenticação. A busca aceita nome,
categoria, localização e destino, com paginação. O abastecimento é feito pela equipe
operadora via importação JSON transacional, sem escrita pública. No Docker Compose
de desenvolvimento, um seed carrega exemplos automaticamente se o catálogo estiver vazio
(desative com `SEED_CATALOGO=false`). Avaliações e filtro
por nota ficam para a #23. Veja [contrato, importação e exemplos](docs/catalogo-atividades.md).

## Painel pessoal de viagens — RF06

`GET /viagens?pagina=1&tamanho_pagina=20` exige `Authorization: Bearer <token>`.
Retorna viagens criadas pelo usuário e compartilhadas com ele, sem duplicação.
Cada item contém os campos da viagem (`id`, `criador_id`, `nome`, `descricao`,
`data_inicio`, `data_fim`, `status`, `criado_em`, `atualizado_em`) e
`papel_usuario`: `criador`, `editor` ou `visualizador`. Códigos de convite não são expostos.

A resposta é um objeto com `itens`, `pagina`, `tamanho_pagina` e `tem_proxima`.
Por exemplo, para uma conta sem viagens:

```json
{"itens": [], "pagina": 1, "tamanho_pagina": 20, "tem_proxima": false}
```

A página começa em 1; o tamanho padrão é 20, com mínimo 1 e máximo 100.
Parâmetros inválidos retornam 422; token ausente ou inválido retorna 401.
A ordenação é crescente por `data_inicio`, com desempate por `id`.
Uma página além do fim retorna `itens: []` e `tem_proxima: false`.
A paginação usa deslocamento: sem alterações nos dados, páginas sucessivas não
repetem itens; inserções, exclusões ou mudanças de datas entre requisições podem
mudar sua composição. Cada nova consulta reflete os vínculos e papéis atuais,
inclusive a remoção de colaboradores.

**Mudança de contrato:** o endpoint antes retornava uma lista simples. Clientes
agora devem ler `itens` e usar os metadados para navegar pelas páginas.
Não é necessário alterar o esquema do banco para esta funcionalidade.

## Arquitetura

A documentação oficial descreve uma arquitetura cliente-servidor com frontend separado, API REST, PostgreSQL e serviços externos de mapas e locais/atividades. Prevê um catálogo interno enriquecido com Google Places, preservando as avaliações próprias e os dados associados às viagens. Essas integrações ainda não existem neste repositório.

O documento de arquitetura menciona NextJS para o frontend e NestJS para o backend, embora sua tabela de restrições deixe linguagem e framework a definir. A implementação atual utiliza Python e FastAPI. A organização hexagonal descrita abaixo corresponde ao código presente; a divergência de stack permanece pendente de alinhamento na documentação oficial.

O backend segue a **Arquitetura Hexagonal (Ports and Adapters)**. As regras de domínio e os casos de uso ficam no núcleo da aplicação, enquanto HTTP, persistência e bibliotecas de segurança são integrados por adaptadores.

Essa separação permite exercitar os casos de uso com um repositório em memória e utilizar PostgreSQL na API, mantendo os mesmos contratos de persistência.

| Camada | Responsabilidade no projeto |
|---|---|
| `domain` | Define as entidades `Usuario` e `Viagem`, a matriz de permissões por viagem (`permissoes.py`), os contratos `UsuarioRepository`, `ViagemRepository`, `MembroViagemRepository`, `PasswordHasher` e `TokenService`, o vocabulário fechado do domínio (`enums.py`: papéis, status, categorias, tipos de notificação) e as constantes das regras de negócio (`regras.py`) |
| `application` | Coordena os casos de uso de usuários (incluindo logout e recuperação de senha) e de viagens; `PoliticaAcessoViagem` centraliza a autorização das operações sobre uma viagem |
| `adapters/inbound` | Recebe requisições HTTP, valida contratos com Pydantic e converte resultados em respostas da API |
| `adapters/outbound` | Implementa persistência com SQLAlchemy ou memória, hash com bcrypt, tokens com PyJWT e envio de email por SMTP |
| `infrastructure` | Centraliza configurações, conexão e sessões do banco de dados |

Em uma operação de cadastro, por exemplo, a rota recebe os dados e chama `CriarUsuario`. O caso de uso consulta o repositório para verificar duplicidade de email, solicita o hash da senha e salva a entidade. As implementações concretas de persistência e hashing são fornecidas ao caso de uso pela camada de entrada.

O domínio e os casos de uso não dependem de FastAPI, Pydantic ou SQLAlchemy. A montagem da aplicação e o registro das rotas ficam em `app/main.py`.

## Tecnologias

O comando `docker compose up -d --build` tambem inicia o MiniStack e provisiona
o ElastiCache local via AWS CLI e CloudFormation. Apos o deploy, o PostgreSQL inicia;
a API aguarda o banco ficar saudavel e executa as migracoes antes do servidor.
O endpoint protegido `GET /usuarios/resumo` usa o Redis para guardar o total de usuarios
por 60 segundos. Cadastro e exclusao invalidam essa contagem. `X-Cache` indica HIT, MISS
ou BYPASS; a autenticacao continua consultando o banco. Veja o [roteiro de infraestrutura e demonstracao](infra/README.md).

| Tecnologia | Papel |
|---|---|
| Python | Linguagem do backend; a imagem Docker utiliza Python 3.13 |
| FastAPI e Uvicorn | API HTTP e servidor da aplicação |
| Pydantic | Validação dos dados de entrada e definição dos contratos de resposta |
| SQLAlchemy e PostgreSQL | Mapeamento e armazenamento relacional dos dados |
| Alembic | Versionamento e aplicação de alterações no banco |
| bcrypt | Geração e verificação de hashes de senha |
| PyJWT | Emissão e validação de tokens JWT |
| Redis / ElastiCache local | Cache da contagem de usuarios, provisionado via CloudFormation no MiniStack |
| Docker Compose | Inicializacao do MiniStack, deploy AWS CLI, PostgreSQL e API |
| Mailpit | Servidor SMTP falso do ambiente local: captura os emails da API e os exibe em http://localhost:8025 |
| pytest | Testes automatizados de domínio, aplicação e integração |

## API HTTP

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| `GET` | `/health` | Público | Verifica se a API está respondendo |
| `POST` | `/usuarios` | Público | Cadastra um usuário |
| `POST` | `/auth/login` | Público | Autentica e retorna o token de acesso |
| `POST` | `/auth/logout` | JWT | Encerra a sessão do token enviado |
| `POST` | `/auth/recuperar-senha` | Público | Envia por email um link de redefinição de senha |
| `POST` | `/auth/redefinir-senha` | Público | Define uma nova senha com o token recebido por email |
| `GET` | `/usuarios/resumo` | JWT | Consulta o total de usuarios, com cache Redis e header X-Cache |
| `GET` | `/usuarios/me` | JWT | Consulta o perfil autenticado |
| `PATCH` | `/usuarios/me` | JWT | Atualiza nome e/ou email |
| `PATCH` | `/usuarios/me/senha` | JWT | Altera a senha da conta |
| `DELETE` | `/usuarios/me` | JWT | Exclui a conta autenticada |
| `POST` | `/viagens` | JWT | Cria uma viagem; o criador é o usuário do token |
| `GET` | `/viagens` | JWT | Lista as viagens criadas pelo usuário ou das quais ele é colaborador |
| `GET` | `/viagens/{viagem_id}` | JWT + participante | Consulta uma viagem |
| `PATCH` | `/viagens/{viagem_id}` | JWT + criador ou editor | Altera nome, descrição, datas e/ou status |
| `DELETE` | `/viagens/{viagem_id}` | JWT + criador | Exclui a viagem com colaboradores, roteiro e orçamento |

Os contratos completos, exemplos e respostas estão disponíveis no Swagger UI em [http://localhost:8000/docs](http://localhost:8000/docs), com a aplicação em execução. O documento OpenAPI fica em `/openapi.json`.

A proteção das rotas de conta é feita pela dependência `get_usuario_atual`. Tokens ausentes, inválidos, expirados, encerrados por logout ou por troca de senha e tokens de contas excluídas resultam em resposta `401`. O JWT utiliza o algoritmo HS256, tem validade padrão de 60 minutos e carrega `jti` (identificador da sessão) e `ver` (versão das sessões do usuário). A lista de tokens revogados fica no PostgreSQL, não no Redis, e uma falha ao consultá-la nunca autoriza a requisição. As claims `sub`, `exp`, `jti` e `ver` são obrigatórias, e `sub` precisa ser o identificador numérico positivo emitido pelo login. Tokens sem essas claims, com outro algoritmo ou sem assinatura (`alg: none`) também resultam em `401`, nunca em erro interno. Detalhes em [`docs/sessoes-e-logout.md`](docs/sessoes-e-logout.md).

### Viagens e permissões

O usuário autenticado cria uma viagem com nome, descrição opcional e datas de início e fim; a data de fim não pode ser anterior à de início. Toda viagem nasce com status `planejando` e pode passar livremente para `confirmada` ou `concluida` (RF07). O criador é sempre o usuário do token: um `criador_id` enviado no corpo é ignorado. Na criação também é gerado o código de convite, que ainda não é exposto pela API.

A autorização fica em `PoliticaAcessoViagem` (aplicação), que consulta a matriz de `app/domain/permissoes.py`. Os próximos módulos (destinos, atividades, orçamento, membros) devem usar a mesma política.

| Ação | Criador | Editor | Visualizador | Outro usuário |
|---|---|---|---|---|
| Consultar a viagem | Sim | Sim | Sim | `404` |
| Editar dados gerais e status | Sim | Sim | `403` | `404` |
| Excluir a viagem | Sim | `403` | `403` | `404` |
| Gerenciar membros (futuro) | Sim | `403` | `403` | `404` |

Quem não participa da viagem recebe `404`, a mesma resposta de uma viagem inexistente, para não revelar ids de viagens alheias. A exclusão remove colaboradores, roteiro e orçamento pela cascata do banco, na mesma transação.

## Dados e persistência

A entidade `Usuario` representa a conta e contém `id`, `nome`, `email`, `senha_hash` e `criado_em`. Ela rejeita nome, email e hash vazios. A validação do formato do email e dos contratos HTTP fica nos schemas Pydantic; a verificação de email duplicado ocorre nos casos de uso de cadastro e atualização.

Na persistência, a tabela `usuarios` possui identificador inteiro gerado automaticamente, uma restrição de unicidade para o email (`usuarios_email_key`) e `criado_em` com fuso horário, preenchido pelo banco no cadastro e mantido nas atualizações. A checagem prévia do caso de uso não impede que duas requisições simultâneas cadastrem o mesmo email. Por isso, o repositório converte a violação dessa restrição específica em `EmailDuplicado` (resposta `400`). Outras violações de integridade não são mascaradas como email duplicado. A API utiliza `SQLAlchemyUsuarioRepository`; a implementação `UsuarioRepositoryMemory`, que aplica a mesma regra de unicidade, está disponível como alternativa para testes.

As migrações em `alembic/versions/` provisionam somente o schema; elas não criam contas. Elas criam a tabela de usuários e, em seguida, o esquema de viagens descrito abaixo (migração `a3f1c9d27b45`, que também adiciona `usuarios.criado_em`; contas existentes recebem o horário da migração) e a tabela `tokens_revogados` e a coluna `usuarios.versao_sessao`, usadas pelo logout e pela troca de senha (migração `b7e4d2a91c03`). A revisão `c86992485fcc`, que antes inseria uma conta de demonstração, permanece na cadeia sem alterar dados. A revisão `7059dc664d50` só converte para bcrypt uma conta `usuario@viajajunto.com` que ainda tenha a senha original do seed em texto puro, e nunca sobrescreve uma senha já definida. No ambiente Docker Compose, as migrações pendentes são aplicadas antes da inicialização da API. Os dados do PostgreSQL são mantidos em um volume Docker.

A conta de demonstração (`usuario@viajajunto.com` / `changeme123`) é criada à parte, apenas em desenvolvimento:

```sh
python -m app.adapters.inbound.cli.seed_demo
```

O comando usa o caso de uso de cadastro, é recusado quando `APP_ENV` não é `development` nem `test` e mantém sem alterações uma conta que já exista com esse email. O Compose local o executa automaticamente após as migrações quando `APP_ENV=development`. Bancos migrados antes dessa mudança continuam com a conta de demonstração; remova-a manualmente em ambientes que não sejam de desenvolvimento.

O modelo oficial prevê também `viagem`, `membro_viagem`, `destino_catalogo`, `destino_viagem`, `catalogo_atividade`, `atividade_viagem`, `orcamento` e `avaliacao`. Ele distingue os dados reutilizáveis do catálogo das informações de cada viagem: por exemplo, a atividade do catálogo descreve um local ou experiência, enquanto sua associação à viagem registra horário, custo previsto e status. Cada viagem possui um orçamento, e as avaliações se vinculam às atividades do catálogo.

Essas tabelas, mais `notificacoes` e `tokens_recuperacao_senha`, foram criadas pela migração `a3f1c9d27b45` conforme as decisões de [`docs/decisoes-de-produto.md`](docs/decisoes-de-produto.md): identificadores inteiros com o código de convite em coluna própria, avaliação de atividades com ranking de destinos derivado, papéis, validade de convites, datas, moeda e efeitos das exclusões. Viagens e membros já têm repositórios (`SQLAlchemyViagemRepository`, `SQLAlchemyMembroViagemRepository`); `tokens_recuperacao_senha` é usada pela recuperação de senha; as demais tabelas ainda são apenas esquema. A migração `e2c7a4f19d36` alinhou os status de viagem ao RF07 (`planejando`, `confirmada`, `concluida`). A tabela `usuarios` ganhou o campo `criado_em` previsto no documento; ela mantém o nome `usuarios` em vez de `usuario`.

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
│   ├── inbound/cli/       # Comandos de linha (seed de demonstração)
│   └── outbound/          # Persistência e implementações de segurança
├── infrastructure/       # Configuração e acesso ao banco
└── main.py               # Criação da aplicação FastAPI
alembic/                  # Migrações do banco de dados
docs/                     # Decisões de produto, modelo de dados, sessões e recuperação de senha
tests/
├── domain/               # Validações da entidade Usuario
├── application/          # Casos de uso com repositório em memória
├── infrastructure/       # Validação da configuração de ambiente
└── integration/          # API, persistência e modelo de dados com PostgreSQL
```

## Execução local

Com Docker e Docker Compose disponíveis, crie um arquivo `.env` a partir de `.env.example` e execute, na raiz deste repositório:

```sh
docker compose up -d --build
```

O Compose inicia o PostgreSQL, aguarda o banco ficar saudável, aplica as migrações e disponibiliza a API na porta `8000`. O ambiente utiliza recarga automática ao editar os arquivos da aplicação. Também sobe o Mailpit: os emails enviados pela API (recuperação de senha) aparecem em [http://localhost:8025](http://localhost:8025) e nunca saem para a internet. Veja [`docs/recuperacao-de-senha.md`](docs/recuperacao-de-senha.md#como-ver-os-emails-no-ambiente-de-teste).

A configuração da API utiliza `APP_ENV`, `DATABASE_URL`, `JWT_SECRET_KEY` e `JWT_EXPIRE_MINUTES`. O Compose fornece `DATABASE_URL` diretamente ao container da API e repassa `APP_ENV` (padrão `development`), `JWT_SECRET_KEY` e `JWT_EXPIRE_MINUTES` a partir do `.env`.

A configuração é validada na inicialização. Com `APP_ENV` igual a `development` ou `test`, uma `JWT_SECRET_KEY` vazia usa a chave de exemplo. Em qualquer outro ambiente, a API não sobe se a chave estiver ausente, se for a chave de exemplo ou se tiver menos de 32 bytes. A mensagem de erro não exibe o valor da chave. A imagem Docker define `APP_ENV=production` por padrão. Portanto, ao executá-la fora do Compose local, forneça uma chave própria, por exemplo gerada com `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

## Testes

A suíte contempla validações da entidade, regras dos casos de uso, autenticação, gerenciamento de conta e persistência. Os testes de domínio e aplicação usam o repositório em memória; os testes de integração dependem de PostgreSQL acessível e do schema criado pelas migrações.

Com as dependências instaladas no ambiente Python, a suíte pode ser executada com `pytest`. Para executar somente os testes sem banco:

```sh
pytest tests/domain tests/application
```

Os testes de integração exigem um PostgreSQL exclusivo e falham se ele estiver indisponível. Inicie-o com `docker compose --profile test up -d db_test`; o banco padrão é `viajajunto_test`, na porta 5433. As migrações são aplicadas pela suíte e as gravações de cada teste são desfeitas.

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

## Escopo e evolução

O módulo de usuários estabelece a base de autenticação, persistência e organização arquitetural do ViajaJunto. A evolução prevista contempla os módulos descritos nos requisitos, incluindo autorização por viagem e as integrações de catálogo e mapas previstas na arquitetura.

O catálogo público de atividades e sua importação operacional estão documentados em `docs/catalogo-atividades.md`.

Este repositório contém apenas o backend. A interface web e os recursos de colaboração no planejamento de viagens ainda não estão presentes nesta implementação.

Estão fora do escopo da versão especificada: reservas de hotéis, voos e ingressos por APIs externas; chat em tempo real; aplicativo mobile nativo; pagamentos e divisão de custos; edição simultânea em tempo real; e gamificação de avaliações. A integração de catálogo com Google Places prevista na arquitetura não corresponde a uma integração de reservas.

## Referências de especificação

Esta descrição considera os documentos oficiais fornecidos pela equipe: `index.md` (visão geral), `requirements.md` (requisitos e regras de negócio) e `architecture.md` (arquitetura e modelo de dados). Os documentos de requisitos e arquitetura identificam a revisão inicial como versão 0.1, de 25/08/2026. Esses arquivos foram consultados externamente e não estão incluídos neste repositório.

Além da divergência de stack, há pontos que precisam de alinhamento entre os documentos: a visão geral e algumas regras mencionam avaliações de destinos, enquanto RF22–RF24 e o modelo relacional descrevem avaliações de atividades; o identificador de viagem é descrito como string/código de convite, mas as chaves estrangeiras correspondentes aparecem como inteiros. Este README registra essas diferenças sem definir uma solução que ainda não foi formalizada pela equipe.
