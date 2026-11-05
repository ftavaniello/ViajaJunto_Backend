# Roteiro da demonstração pelo Swagger

Duração sugerida: 12 a 15 minutos. Fluxo: consultar o roteiro, planejar uma
atividade, acompanhar o orçamento, colaborar com permissões diferentes e avaliar.
Abra <http://localhost:8000/docs> com a API em execução.

## Preparação

Os IDs e as datas abaixo foram conferidos no banco local em 04/11/2026, com o
seed `dados-iniciais-v2` criado com referência em 03/11/2026. Não são IDs universais:
em outro banco, confira as respostas das consultas iniciais e substitua os valores.
As datas precisam estar dentro da estadia atual da parada.
Após o reset de 05/11/2026, Orlando vai de 05/12 a 10/12; a data de inclusão
05/12 usada abaixo continua válida.

Este roteiro pressupõe a versão do seed que reserva Disney Springs para a demo
e inclui Ana como Editora e Visualizadora em outras viagens. Bancos já preenchidos
não são atualizados automaticamente; use o [reset explícito](reset-banco.md) para
recarregar os cenários depois de atualizar o código.

| Item | Valor usado |
| --- | --- |
| Viagem Orlando e Miami em grupo | `viagem_id = 1` |
| Parada de Orlando na viagem | `destino_id = 1` |
| Orlando no catálogo | `destino_catalogo_id = 1` |
| Disney Springs no catálogo | `catalogo_atividade_id = 3` |
| Estadia em Orlando após reset de 05/11 | `2026-12-05` a `2026-12-10` |
| Data da atividade da demo | `2026-12-05` |
| Nova ocorrência no roteiro | `A`: copiar o ID retornado pelo POST da etapa 4 |

A senha inicial das quatro contas usadas é `DemoViaja123!`. Se tiver sido alterada,
use a senha atual. A cada login, substitua o token em **Authorize** pelo novo
`access_token`. Não inclua tokens reais neste documento.

## 1. Entrar como Criador e consultar a viagem

**POST `/auth/login` — seção Autenticação**

```json
{
  "email": "criador.demo@example.com",
  "senha": "DemoViaja123!"
}
```

Copie `access_token` para **Authorize** e execute:

| Endpoint | Parâmetros | O que mostrar |
| --- | --- | --- |
| GET `/usuarios/me` — seção Usuarios | Nenhum | Identidade obtida pelo token |
| GET `/viagens` — seção Viagens | `pagina = 1`, `tamanho_pagina = 20`; demais filtros vazios | Viagens acessíveis ao usuário; apontar `papel_usuario` como criador, editor e visualizador |
| GET `/viagens/{viagem_id}` — seção Viagens | `viagem_id = 1` | Nome e período do roteiro da Flórida |
| GET `/viagens/{viagem_id}/destinos` — seção Roteiro | `viagem_id = 1` | Orlando e Miami, ordem e estadias |

Na primeira página, localize também **Roma com amigos** (`editor`) e
**Miami entre amigos** (`visualizador`). Se necessário, filtre pelo nome da viagem.
Disney Springs permanece no catálogo, mas ainda não está na agenda da Flórida.

Fala sugerida: “Uma viagem pode ter várias paradas, cada uma com sua própria
estadia e agenda.”

## 2. Ver a agenda atual e descobrir atividades em Orlando

Primeiro, abra a seção **Atividades do roteiro** do Swagger.

**GET `/viagens/{viagem_id}/destinos/{destino_id}/atividades` — seção Atividades do roteiro**

Parâmetros: `viagem_id = 1`, `destino_id = 1`.

Mostre as cinco atividades já planejadas para Orlando: Magic Kingdom Park,
Universal Studios Florida, ICON Park, East End Market e Lake Eola Park.
Confira na resposta que **Disney Springs ainda não está na agenda**.
Mostre que as atividades já vêm ordenadas por data e horário: Magic Kingdom Park
em 05/12 às 09h, seguido de Universal Studios Florida em 06/12 às 14h.
Essa é a ordem cronológica da agenda, não a ordenação do catálogo público.

Fala sugerida: “Estes são os passeios que o grupo já planejou para Orlando.
Vamos consultar o catálogo para ver o que mais podemos fazer na cidade.”

Agora, abra a seção **Catálogo**.

**GET `/catalogo/atividades` — seção Catálogo**

| Parâmetro | Valor |
| --- | --- |
| `localizacao` | `Orlando` |
| `pagina` | `1` |
| `tamanho_pagina` | `20` |

Deixe `nome`, `categoria`, `nota_minima` e `destino_catalogo_id` vazios.
Assim a pesquisa usa a cidade, sem restringir o resultado a Disney Springs.
A localização faz busca textual por cidade, país ou endereço; com o seed atual,
a resposta inclui as seis atividades de Orlando.

Mostre Disney Springs entre os resultados e anote seu ID de catálogo, **3**.

Fala sugerida: “Disney Springs está no catálogo, mas não está no nosso roteiro.
Quero incluir esse passeio na viagem.”

## 3. Consultar o orçamento antes da inclusão

**GET `/viagens/{viagem_id}/orcamento` — seção Orçamento**, com `viagem_id = 1`.

Anote `total_planejado` e `saldo_disponivel` da resposta. Use esses valores como
base da comparação, pois o banco pode conter alterações de ensaios anteriores.

## 4. Adicionar Disney Springs ao roteiro

**POST `/viagens/{viagem_id}/destinos/{destino_id}/atividades` — seção Atividades do roteiro**

Parâmetros: `viagem_id = 1`, `destino_id = 1`.

Antes de executar, comente: “Vou agendar Disney Springs em 05/12 às 10h,
entre Magic Kingdom Park, em 05/12 às 09h, e Universal Studios Florida,
em 06/12 às 14h. Ao consultar novamente, ela deve aparecer nessa posição,
mesmo tendo sido cadastrada por último.”

```json
{
  "catalogo_atividade_id": 3,
  "data": "2026-12-05",
  "hora_inicio": "10:00:00",
  "duracao_minutos": 120,
  "custo_previsto": "150.00",
  "status": "pendente"
}
```

Copie o `id` retornado como **A**. Sempre substitua `A` pelo número real nos
campos `atividade_id` das próximas etapas.

| Consulta | Resultado esperado |
| --- | --- |
| GET `/viagens/1/destinos/1/atividades` — seção Atividades do roteiro | Disney Springs aparece entre Magic Kingdom Park e Universal Studios Florida |
| GET `/viagens/1/orcamento` — seção Orçamento | Total planejado aumenta R$ 150 e saldo diminui R$ 150 |

Na resposta do GET da agenda, destaque esta sequência:

| Posição | Atividade | Data | Horário |
| --- | --- | --- | --- |
| 1 | Magic Kingdom Park | 05/12/2026 | 09h |
| 2 | **Disney Springs** | 05/12/2026 | **10h** |
| 3 | Universal Studios Florida | 06/12/2026 | 14h |
| 4 | ICON Park | 08/12/2026 | 14h |
| 5 | East End Market | 09/12/2026 | 09h |
| 6 | Lake Eola Park | 10/12/2026 | 14h |

Fala sugerida: “A atividade foi incluída por último, mas a API a retornou na
posição correspondente à data e ao horário, atendendo à agenda cronológica.”
A duração é estimativa; este exemplo demonstra ordenação, sem validar conflito
entre os horários dos passeios. Após a edição para 11h na etapa 5, Disney Springs
continua entre Magic Kingdom e Universal.

Fala sugerida: “O catálogo descreve o lugar. Data, horário, custo e status
pertencem ao planejamento deste grupo.”

## 5. Alterar o planejamento como Editor

**POST `/auth/login` — seção Autenticação** e substituir o token em **Authorize**:

```json
{
  "email": "editor.demo@example.com",
  "senha": "DemoViaja123!"
}
```

**PATCH `/viagens/{viagem_id}/destinos/{destino_id}/atividades/{atividade_id}` — seção Atividades do roteiro**

Parâmetros: `viagem_id = 1`, `destino_id = 1`, `atividade_id = A`.

```json
{
  "hora_inicio": "11:00:00",
  "custo_previsto": "250.00"
}
```

A alteração deve ser aceita. Consulte **GET `/viagens/1/orcamento` — seção Orçamento**: o total
planejado aumenta mais R$ 100, e o saldo diminui no mesmo valor. Mostre também a
distribuição por tipo. A alteração de horário gera o aviso usado na próxima etapa.

## 6. Consultar e testar a restrição do Visualizador

**POST `/auth/login` — seção Autenticação** e substituir o token:

```json
{
  "email": "visualizador.demo@example.com",
  "senha": "DemoViaja123!"
}
```

| Chamada | Parâmetros | Resultado esperado |
| --- | --- | --- |
| GET `/viagens/{viagem_id}/destinos` — seção Roteiro | `viagem_id = 1` | `200`: consulta permitida |
| GET `/notificacoes` — seção Notificações | Manter padrões | Localizar o aviso da alteração do horário |
| PATCH da ocorrência, abaixo — seção Atividades do roteiro | `viagem_id = 1`, `destino_id = 1`, `atividade_id = A` | `403`: alteração proibida |

Na seção **Atividades do roteiro**, use o mesmo endpoint PATCH da etapa 5 e envie:

```json
{
  "hora_inicio": "12:00:00"
}
```

A tentativa deve ser recusada. Consulte **GET `/viagens/1/destinos/1/atividades` — seção Atividades do roteiro**
e confira que a ocorrência A continua às **11h**.

Fala sugerida: “Os participantes compartilham o roteiro, mas as permissões são
verificadas em cada operação.”

## 7. Demonstrar isolamento de uma viagem privada

**POST `/auth/login` — seção Autenticação** e substituir o token:

```json
{
  "email": "externo.demo@example.com",
  "senha": "DemoViaja123!"
}
```

**GET `/viagens/{viagem_id}` — seção Viagens**, com `viagem_id = 1`.

Resultado esperado: **404**, pois essa conta não participa da viagem.

## 8. Concluir a atividade e publicar uma avaliação

Antes de avaliar, na seção **Catálogo**, execute **GET
`/catalogo/destinos/ranking`**, com `limite = 10`, duas vezes. Em **Response headers**,
mostre `x-cache`: `MISS` na primeira consulta e `HIT` na segunda. Se o ranking já
estiver cacheado, a primeira também pode ser `HIT`; após o TTL (60 segundos por
padrão), uma nova consulta volta a `MISS`.

Fala sugerida: “O ranking é público e compartilhado. Redis evita repetir a
agregação das avaliações a cada acesso. Vamos publicar uma avaliação e observar
a invalidação desse resultado.”


Na seção **Autenticação**, use **POST `/auth/login`** novamente como `criador.demo@example.com`, com senha `DemoViaja123!`,
e substitua o token em **Authorize**.

**PATCH `/viagens/{viagem_id}/destinos/{destino_id}/atividades/{atividade_id}` — seção Atividades do roteiro**

Parâmetros: `viagem_id = 1`, `destino_id = 1`, `atividade_id = A`.

```json
{
  "status": "concluida"
}
```

Mostre os campos que registram a realização. A conclusão é declarada pelo grupo,
não uma comprovação externa de presença.

**PUT `/viagens/{viagem_id}/destinos/{destino_id}/atividades/{atividade_id}/avaliacao` — seção Avaliações**

Use os mesmos parâmetros:

```json
{
  "nota": 5,
  "comentario": "Gostamos do passeio em grupo pelo Disney Springs."
}
```

Consulte os resultados públicos:

| Endpoint | Parâmetros |
| --- | --- |
| GET `/catalogo/atividades/{atividade_id}/avaliacoes` — seção Catálogo | `atividade_id = 3`, `pagina = 1`, `tamanho_pagina = 20` |
| GET `/catalogo/atividades/{atividade_id}` — seção Catálogo | `atividade_id = 3` |

Aqui o ID é **3, do catálogo**, e não A, da ocorrência privada. Se o usuário já
avaliou Disney Springs, o PUT atualiza sua avaliação existente, sem duplicá-la.

Após o PUT de avaliação, retorne à seção **Catálogo** e execute **GET
`/catalogo/destinos/ranking`**, com `limite = 10`: espere `x-cache: MISS`; repetindo,
espere `HIT`. A publicação invalida o ranking, mesmo que a posição dos destinos
não mude. `BYPASS` significa que o cache está indisponível, com fallback para SQL.

## 9. Encerrar com os dados geográficos

**GET `/viagens/{viagem_id}/mapa` — seção Mapa**, com `viagem_id = 1`.

Mostre Orlando e Miami, suas coordenadas e a ordem das paradas. O backend fornece
os pontos; a renderização do mapa pertence ao frontend.

Se houver tempo, consulte também **GET `/usuarios/me/paises-visitados` — seção Mapa** e
**GET `/catalogo/destinos/ranking` — seção Catálogo**, mantendo os parâmetros padrão. Países
visitados dependem do status e da data de chegada, não apenas de existir uma parada.

## Ensaios e repetição

- Se Disney Springs já aparecer na consulta inicial por causa de um ensaio,
  remova somente a ocorrência criada no ensaio antes de repetir a inclusão.
  Não remova as atividades originais do seed.
- Cada POST da etapa 4 cria outra ocorrência e soma seu custo. Para continuar o
  mesmo ensaio, reutilize A nas edições em vez de executar novamente o POST.
- Para remover apenas a ocorrência do ensaio, use a seção **Atividades do roteiro**, endpoint
  **DELETE `/viagens/{viagem_id}/destinos/{destino_id}/atividades/{atividade_id}`**, como
  Criador ou Editor, com `viagem_id = 1`, `destino_id = 1`, `atividade_id = A`.
  Isso retira seu custo do orçamento, mas preserva a avaliação pública.
- Reiniciar a API não desfaz as alterações. O seed não sobrescreve os dados.
- Confira as contas, os IDs e as datas antes da apresentação. Não é necessário
  resetar o banco para executar este roteiro.

Referências: [seed](seed-demonstracao.md), [atividades](atividades-roteiro.md),
[orçamento](orcamento-viagem.md) e [avaliações](avaliacoes-atividades.md).
