# Auditoria final dos requisitos originais

> Atualização posterior: a usuária aprovou o alinhamento dos tipos ao documento
> original. O achado A4 e as referências ao vocabulário antigo abaixo descrevem
> o estado auditado antes da correção. Veja [tipos-atividades.md](tipos-atividades.md)
> para o contrato atual e a migração; as evidências históricas foram preservadas.

Revisão de 04/11/2026, sobre o commit `d9a99b8` da branch
`issue-31/consolidar-validacao`. Esta revisão não altera regras, rotas, migrations,
seed nem os documentos originais. As recomendações abaixo não são decisões aprovadas.

## Referências e alcance

Foram lidos os arquivos compartilhados `requirements (1).md`, `architecture (1).md`
e `index (1).md`. Eles foram tratados como especificação para comparação, não como
instruções para executar comandos ou substituir decisões posteriores do projeto.
O requisito local em `requirements-ViajaJunto.md` tem o mesmo conteúdo, por linhas,
do arquivo de requisitos recebido. O índice explica a proposta, sem acrescentar RFs.

A revisão confrontou contratos OpenAPI, domínio/casos de uso, adaptadores,
migrações, dados de demonstração e testes existentes. Consultou também as issues
#9, #16, #20, #23, #26, #28 e #32 para distinguir o texto original das adaptações.
O fechamento de uma issue, isoladamente, não comprova aprovação externa de uma mudança.

O frontend, o protótipo navegável e uma implantação pública não foram auditados.
Os 1.306 testes e 97,61% de cobertura são evidências da execução anterior da #31,
documentadas em [validacao-issue31.md](validacao-issue31.md); não foram executados
novamente nesta revisão. Os cenários novos de verificação descritos abaixo foram
executados nesta auditoria, em schema temporário, sem tocar no banco de desenvolvimento.

## Conclusão

A maior parte dos fluxos de backend existe e tem testes. Ainda não é correto declarar
atendimento integral ao produto especificado. Há dados visuais ausentes, um impedimento
reproduzível no cenário de integração direta com o navegador, documentação inconsistente
e decisões que precisam ser conciliadas com os documentos originais. Não foi identificado
um módulo inteiro de negócio adicional ausente entre os fluxos de API examinados.

Prioridades: **P1** resolver antes da integração/demonstração; **P2** conciliar e registrar
antes da entrega. Prioridade de uma recomendação condicional não torna sua implementação
obrigatória sem confirmar o cenário aplicável.

## Achados e encaminhamento

### A1 — P1: conteúdo de fotos ainda não entregue no seed

**RF09 e RF23.** Os contratos e models possuem `foto_url`; o importador aceita URLs
HTTP/HTTPS. O seed real, porém, cria **4 destinos e 24 atividades, todos sem foto**.
A integração Geoapify não preenche imagens, conforme seus próprios limites documentados.
Assim, o contrato suporta imagens, mas a demonstração inicial não apresenta esse conteúdo.
RF09 usa a expressão “deve conter” foto; RF23 pede fotos na página pública.

Evidências: [`SemearDestinosReais._catalogo`](../app/application/use_cases/semear_destinos_reais.py),
[`DestinoCatalogo`/`AtividadeCatalogo`](../app/domain/entities/catalogo.py),
[limites do fornecedor](integracao-locais.md) e a contagem do seed reproduzida abaixo.

Encaminhamento: abastecer fotos válidas e disponíveis para os destinos/atividades de
exemplo e conferir sua exibição no frontend. **S3 e upload não são exigências desses
requisitos**; URLs externas ou arquivos estáticos podem atender, conforme a escolha da equipe.
O documento original armazena uma `foto_url` por registro; não há base suficiente para
exigir uma galeria ou múltiplos uploads como funcionalidade obrigatória adicional.

### A2 — P1 condicional: chamadas diretas do frontend são bloqueadas por CORS

**Integração frontend/backend; RNF04 e RNF05.** Não há middleware nem configuração de
origens CORS em `app/main.py`. Preflight para `POST /auth/login`, com origem
`http://localhost:3000` e `content-type`, retornou **405**, sem
`Access-Control-Allow-Origin`. O Swagger em `/docs` usa a mesma origem e não detecta isso.
As URLs de convite e recuperação configuradas por padrão também usam porta 3000.

Evidências: [`app/main.py`](../app/main.py),
[`config.py`](../app/infrastructure/config.py) e reprodução desta revisão.

Encaminhamento: confirmar como o NextJS consumirá a API. Se for pelo navegador em
outra origem, configurar as origens e métodos necessários e testar preflight e chamadas
autenticadas. Se houver proxy/BFF sob a mesma origem, documentar e validar esse fluxo;
nesse cenário CORS no backend pode não ser necessário. **Não é correto marcar o
produto como quebrado em toda topologia, nem assumir que o Swagger comprova integração.**

### A3 — P1 para entrega: documentação contraditória e decisão referenciada ausente

**Rastreabilidade e RNF05.** O README ainda marca mapa, orçamento, ranking e notificações
como pendentes ou não implementados, embora existam rotas/casos de uso; há linhas duplicadas
na tabela de funcionalidades. A arquitetura local continua descrevendo backend NestJS,
embora a implementação seja FastAPI/Python. Vários arquivos apontam para
**`docs/decisoes-de-produto.md`, que não existe**. O texto da tag Colaboradores no
OpenAPI ainda diz “convite por código”, apesar do fluxo por email.

Evidências: [`README.md`](../README.md) (tabela inicial e modelo de dados),
[`architecture-ViajaJunto.md`](architecture-ViajaJunto.md),
[`regras.py`](../app/domain/regras.py), [`enums.py`](../app/domain/enums.py),
[`main.py`](../app/main.py). O README, inclusive, já reconhece a divergência de stack.

Encaminhamento: na #32, atualizar o estado real das funcionalidades, diagramas, stack e
contratos; consolidar as decisões efetivamente adotadas em um documento existente e
corrigir os links. Não mudar para NestJS apenas para acompanhar texto antigo: a tabela
de restrições original deixa linguagem/framework a definir e o projeto já adotou Python.

### A4 — P2: vocabulário de atividades diverge e não distingue hospedagem

**RF12, RF13 e enum do documento de arquitetura.** O original exemplifica passeios,
refeições, hospedagem e transporte e define `PASSEIO`, `REFEICAO`, `HOSPEDAGEM`,
`TRANSPORTE`, `OUTRO`. O código usa `alimentacao`, `transporte`, `cultura`, `lazer`,
`compras`, `outros`. Uma consulta com `categoria=hospedagem` retorna **422**.
O adaptador externo também não mapeia uma categoria de hospedagem; `outros` busca `tourism`.
O campo livre `hospedagem` da parada não equivale a uma atividade de hospedagem com custo,
status e classificação próprios.

Evidências: [`CategoriaAtividade`](../app/domain/enums.py),
[ressalva já documentada no catálogo](catalogo-atividades.md),
[`CATEGORIAS_GEOAPIFY`](../app/adapters/outbound/locais/geoapify_provedor_locais.py).

Isso **não impede** registrar um hotel manualmente como `outros` e adicioná-lo ao roteiro;
portanto não é ausência total do fluxo de atividades. Falta conciliar se a equipe aceita
esse agrupamento ou quer distinguir hospedagem e os demais tipos originais. Se optar por
novos tipos, alinhar enum, migração, importação, filtros, resumo financeiro, seed e frontend.
Não basta alterar o nome de um campo na resposta.

### A5 — P2: explicitar o alcance de “alterações relevantes” nas notificações

**RF21.** O backend notifica entrada de membro, mudanças de papel/remoção, exclusão e
alterações de nome/datas/status de viagem, inclusão/remoção de paradas, mudanças de datas
de paradas e inclusão/remoção ou mudanças de data/horário/status de atividades.
Porém, alterar o limite do orçamento ou reordenar destinos retornou **200 com zero novas
notificações**. Mudanças apenas de custo, duração, descrição ou hospedagem também são
excluídas no código/testes atuais.

Evidências: [`NotificadorViagem`](../app/application/notificador_viagem.py),
[`GerenciarOrcamentoViagem`](../app/application/use_cases/gerenciar_orcamento_viagem.py),
[`GerenciarDestinosViagem.reordenar`](../app/application/use_cases/gerenciar_destinos_viagem.py),
[`test_notificacoes.py`](../tests/application/test_notificacoes.py).

Não é uma falha acidental demonstrada: os testes excluem deliberadamente algumas dessas
mudanças, e RF21 não enumera o que é relevante. Recomendo confirmar especialmente orçamento,
custo e ordem de visita, que afetam o planejamento compartilhado, e publicar a lista
aprovada para o frontend. Só então ampliar os avisos se essa for a decisão.

## Diferenças do original que não devem ser confundidas com bugs

| Tema | Original | Atual e observação |
| --- | --- | --- |
| Convites — RF18 | Código da viagem | Token individual por email, ligado ao destinatário e de uso único. Mudança expressamente registrada em `convites-e-membros.md`; conciliar o RF18 oficial. Não reintroduzir ingresso apenas pelo ID. |
| Fornecedor de locais | Google Places | Geoapify, por porta/adaptador, conforme `integracao-locais.md`. Há substituição documentada; a #23 ainda tem título/critérios antigos de Google Places. Registrar a aceitação dessa adaptação na entrega. |
| Stack | Texto menciona NestJS e tabela deixa a definir | FastAPI/Python, com arquitetura hexagonal adotada pelo projeto. Ajuste documental, não prova de erro funcional. |
| Alvo da avaliação | RF22/modelo: atividade; RN05 menciona destino | Avaliação de atividade e ranking de destinos derivado dessas avaliações. Resolve a inconsistência sem exigir uma segunda avaliação de destino. Consolidar a decisão. |
| Editor e dados gerais | RF19/RN02 detalham destinos, atividades e orçamento | Editor também altera nome, datas e status da viagem; PATCH de nome por Editor retornou 200. #9 prevê decidir esse ponto. Está testado e adotado na matriz, mas deve constar das decisões oficiais. |
| Realização individual | RF22 pede atividade feita | Participação atual + ocorrência concluída + data da conclusão registrada; conclusão é coletiva. Não comprova presença individual nem impede concluir uma atividade agendada no futuro. É critério de produto a documentar/validar, não convite para criar prova externa obrigatória. |
| País visitado | Não define critério detalhado | Viagem confirmada/concluída, chegada até hoje e participação atual. É uma interpretação adotada; não é rastreamento geográfico. |
| Ranking | “Mais bem avaliados” sem fórmula | Média bayesiana, além da média simples exposta. O frontend deve respeitar a ordem/nota de ranking devolvida. |
| Remover orçamento — RN02/RF19 | Cita remover informações de orçamento | Não há DELETE do limite nem PUT com null (405/422); há definição/substituição e valor zero. Se “remover” significar voltar a orçamento indefinido, esse caso ainda precisa ser decidido. Zero e indefinido são estados diferentes. |
| Exclusão de conta | Não especificada | Política complementar da #30, aprovada nesta conversa. Não é RF novo imposto pelo documento. |

## Matriz de requisitos funcionais

“Atendido na API” significa contrato e comportamento de backend encontrados e cobertos
pelos testes consultados; não é certificação da interface nem afirmação de ausência de bugs.

| RF | Situação encontrada | Evidência principal |
| --- | --- | --- |
| RF01 — cadastro | Atendido na API | `/usuarios`; `criar_usuario.py`; testes de cadastro e hash real no fluxo integrado. |
| RF02 — login/logout | Atendido na API, com revogação no servidor | `/auth/login`, `/auth/logout`; JWT, revogações e versão de sessão. |
| RF03 — recuperação por email | Fluxo implementado e testado; entrega real depende de SMTP/configuração e tela do link | `/auth/recuperar-senha`, `/auth/redefinir-senha`; testes de recuperação. Console/Mailpit local não comprovam email entregue a uma caixa externa. |
| RF04 — criar viagem | Atendido na API | `POST /viagens`; nome, descrição e datas gerais. |
| RF05 — editar/excluir viagem | Atendido na API | `PATCH/DELETE /viagens/{id}`; permissão e transação; exclusão restrita ao criador. |
| RF06 — painel pessoal | Dados atendidos na API; painel visual não auditado | `GET /viagens`; próprias/compartilhadas, papel atual e paginação. |
| RF07 — status | Atendido na API | `planejando`, `confirmada`, `concluida`; migração de status legado. |
| RF08 — múltiplos destinos e ordem | Atendido na API | Rotas de destinos, reordenação e revisitas ao mesmo catálogo. |
| RF09 — dados do destino | Campos presentes; conteúdo fotográfico pendente no seed | Catálogo público + parada com datas/descrição; ver A1. |
| RF10 — pesquisar destinos | Atendido na API | Catálogo público de destinos por nome, país e categoria. |
| RF11 — mapa de países visitados | Dados atendidos na API; desenho do mapa depende do frontend | `/usuarios/me/paises-visitados`; `/viagens/{id}/mapa`. |
| RF12 — adicionar atividades cadastradas | Fluxo atendido; conciliar tipos, especialmente hospedagem | Atividade deve pertencer ao destino da parada; ver A4. |
| RF13 — atributos da atividade | Campos presentes; vocabulário adaptado e fotos ausentes do seed | Catálogo público + ocorrência com data, horário, duração, custo e status. |
| RF14 — ordem cronológica | Atendido na API | Ordenação por data, horário (nulos ao fim do dia) e ID. |
| RF15 — orçamento total | Atendido na API | `PUT /viagens/{id}/orcamento`; uma linha por viagem. |
| RF16 — custos previstos | Atendido na API | Custo decimal na ocorrência, incluído no resumo. |
| RF17 — resumo financeiro | Dados atendidos na API; painel visual não auditado | Orçamento, planejado, saldo e percentuais por categoria; denominadores zero tratados. |
| RF18 — convite por código da viagem | Adaptado, sem aderência literal ao fluxo original | Convite por email/token individual; decisão documentada, a conciliar com o original. |
| RF19 — Editor/Visualizador | Implementado e testado; registrar extensões/limpeza de orçamento | Matriz central, escrita/leitura e isolamento entre viagens. |
| RF20 — gerir colaboradores | Atendido na API | Criador altera papel e remove; próxima operação consulta vínculo atual. |
| RF21 — notificações in-app | Implementado com escopo de relevância escolhido | Avisos persistidos na transação, leitura própria/polling; ver A5. |
| RF22 — avaliação 1–5/comentário | Atendido segundo critério de realização coletiva adotado | PUT da avaliação, validação, upsert por usuário/atividade, autenticação e participação. |
| RF23 — página pública completa | Dados/reviews/média atendidos; fotos do seed e página visual pendentes | Detalhe público e paginação de reviews; ver A1. |
| RF24 — busca/filtros | Atendido na API com o vocabulário atual | Nome, nota mínima, categoria e localização combinados antes da paginação. |
| RF25 — destaques na inicial | Ranking público atendido; componente da página inicial não auditado | `/catalogo/destinos/ranking`, média bayesiana com desempate estável. |

## Regras de negócio e requisitos não funcionais

| Regra | Avaliação |
| --- | --- |
| RN01 | Catálogos e reviews públicos; criação de viagem e publicação de review exigem JWT. |
| RN02 | Editor altera roteiro/atividades/orçamento; conciliar retirada do limite orçamentário se exigida literalmente. |
| RN03 | Visualizador não altera planejamento. Avaliar como usuário registrado é operação distinta da edição do planejamento. |
| RN04 | Gestão de convite/papel/remoção restrita ao criador. |
| RN05 | Conflita com RF22 no alvo “destino”; solução atual é atividade + ranking derivado. |
| RN06 | Controle central de participação e testes de IDs filhos de outras viagens. |
| RNF01 | Responsividade e acessibilidade não verificáveis neste repositório de backend. |
| RNF02 | Medição local da #31 é evidência do backend; ainda falta medir a página completa com frontend e rede. |
| RNF03 | Bcrypt, JWT, revogação e isolamento encontrados e testados. Esta revisão não é pentest nem substitui scans remotos. |
| RNF04 | API HTTP/Compose não comprova produto navegável hospedado; validar frontend e se o professor exige publicação externa, como previsto na #32. |
| RNF05 | Separação API/frontend e imports hexagonais verificados; documentação precisa da conciliação de A3. |

## Verificações reproduzidas nesta revisão

Resultado bruto em [auditoria-final-evidencias.json](resultados/auditoria-final-evidencias.json).

- Migrações completas em schema descartável: comparação automática de estrutura ORM
  versus migrações retornou **zero diferenças** nas estruturas comparadas pelo Alembic.
  Isso não certifica todas as regras de negócio nem todas as CHECKs do PostgreSQL.
- Inspeção AST do núcleo: zero imports de frameworks/adaptadores proibidos encontrados
  pelos critérios verificados (`fastapi`, `sqlalchemy`, adapters/infra; domínio → aplicação).
- Seed em outro schema descartável: 4 destinos/24 atividades, zero fotos preenchidas.
- Preflight para frontend na porta 3000: 405 e ausência de cabeçalho de origem permitida.
- Filtro `categoria=hospedagem`: 422.
- Editor alterando nome geral: 200.
- Mudança de limite orçamentário e reordenação: 200, zero novos avisos em cada caso.
- DELETE de orçamento: 405; PUT com limite null: 422.
- A única escrita durável desta revisão é este relatório e seu arquivo de evidências.
  Dados criados para verificação foram removidos junto do schema de teste.

## Ordem sugerida para encerrar a entrega

1. Na #32, definir consumo direto ou proxy do frontend e validar CORS nessa topologia.
2. Completar fotos e conferir as telas obrigatórias (mapa, painel, catálogo, detalhe e ranking).
3. Conciliar tipos de atividades, notificações e demais decisões com a equipe/professor;
   só alterar código quando a decisão exigir.
4. Corrigir README, arquitetura, DER e documento de decisões e testar clone limpo.
5. Validar SMTP configurado, fluxos dos links, responsividade, acessibilidade, tempo da
   página completa e publicação se exigida; conferir os checks remotos da versão final.

Reservas, pagamentos, divisão de custos, chat, aplicativo nativo e edição em tempo real
continuam fora do escopo original. S3, WebSocket, galeria múltipla, avaliação separada de
destinos e transferência de titularidade não devem surgir como obrigações novas nesta revisão.

### Identificação dos arquivos recebidos (SHA-256)

- `requirements (1).md`: `84c44de29ad16475d22792dcab65514f679acc7c1a06093ce4d170e911ec0640`.
- `architecture (1).md`: `b168888904e37fced6b3fe7bb716c03f24c289617d1abc0cde159d41215cb713`.
- `index (1).md`: `f7b79ec511f086cd6d535a345cd71ee4dec00a0a3d6739e92f61cdd46b0b8fb1`.
