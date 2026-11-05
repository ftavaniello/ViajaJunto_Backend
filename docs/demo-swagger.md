# Roteiro da demonstração pelo Swagger

Duração sugerida: 12 a 15 minutos. Fluxo: consultar o roteiro, planejar uma
atividade, acompanhar o orçamento, colaborar com permissões diferentes e avaliar.
Abra <http://localhost:8000/docs> com a API em execução.

## Preparação

Os IDs e as datas abaixo foram conferidos no banco local em 04/11/2026, com o
seed `dados-iniciais-v2` criado com referência em 03/11/2026. Não são IDs universais:
em outro banco, confira as respostas das consultas iniciais e substitua os valores.
As datas precisam estar dentro da estadia atual da parada.

| Item | Valor usado |
| --- | --- |
| Viagem Orlando e Miami em grupo | `viagem_id = 1` |
| Parada de Orlando na viagem | `destino_id = 1` |
| Orlando no catálogo | `destino_catalogo_id = 1` |
| Disney Springs no catálogo | `catalogo_atividade_id = 3` |
| Estadia em Orlando | `2026-12-03` a `2026-12-08` |
| Data da atividade da demo | `2026-12-05` |
| Nova ocorrência no roteiro | `A`: copiar o ID retornado pelo POST da etapa 4 |

A senha inicial das quatro contas usadas é `DemoViaja123!`. Se tiver sido alterada,
use a senha atual. A cada login, substitua o token em **Authorize** pelo novo
`access_token`. Não inclua tokens reais neste documento.

## 1. Entrar como Criador e consultar a viagem

**POST `/auth/login`**

```json
{
  "email": "criador.demo@example.com",
  "senha": "DemoViaja123!"
}
```

Copie `access_token` para **Authorize** e execute:

| Endpoint | Parâmetros | O que mostrar |
| --- | --- | --- |
| GET `/usuarios/me` | Nenhum | Identidade obtida pelo token |
| GET `/viagens` | `pagina = 1`, `tamanho_pagina = 20`; demais filtros vazios | Viagens acessíveis ao usuário |
| GET `/viagens/{viagem_id}` | `viagem_id = 1` | Nome e período do roteiro da Flórida |
| GET `/viagens/{viagem_id}/destinos` | `viagem_id = 1` | Orlando e Miami, ordem e estadias |

Fala sugerida: “Uma viagem pode ter várias paradas, cada uma com sua própria
estadia e agenda.”

## 2. Escolher uma atividade do catálogo

**GET `/catalogo/atividades`**

| Parâmetro | Valor |
| --- | --- |
| `nome` | `Disney Springs` |
| `destino_catalogo_id` | `1` |
| `pagina` | `1` |
| `tamanho_pagina` | `20` |

Deixe os demais filtros vazios, inclusive `nota_minima`. Confirme Disney Springs,
ID `3`. O catálogo é público e descreve os lugares reutilizáveis.

## 3. Consultar o orçamento antes da inclusão

**GET `/viagens/{viagem_id}/orcamento`**, com `viagem_id = 1`.

Anote `total_planejado` e `saldo_disponivel` da resposta. Use esses valores como
base da comparação, pois o banco pode conter alterações de ensaios anteriores.

## 4. Adicionar Disney Springs ao roteiro

**POST `/viagens/{viagem_id}/destinos/{destino_id}/atividades`**

Parâmetros: `viagem_id = 1`, `destino_id = 1`.

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
| GET `/viagens/1/destinos/1/atividades` | Nova ocorrência na agenda cronológica |
| GET `/viagens/1/orcamento` | Total planejado aumenta R$ 150 e saldo diminui R$ 150 |

Fala sugerida: “O catálogo descreve o lugar. Data, horário, custo e status
pertencem ao planejamento deste grupo.”

## 5. Alterar o planejamento como Editor

**POST `/auth/login`** e substituir o token em **Authorize**:

```json
{
  "email": "editor.demo@example.com",
  "senha": "DemoViaja123!"
}
```

**PATCH `/viagens/{viagem_id}/destinos/{destino_id}/atividades/{atividade_id}`**

Parâmetros: `viagem_id = 1`, `destino_id = 1`, `atividade_id = A`.

```json
{
  "hora_inicio": "11:00:00",
  "custo_previsto": "250.00"
}
```

A alteração deve ser aceita. Consulte **GET `/viagens/1/orcamento`**: o total
planejado aumenta mais R$ 100, e o saldo diminui no mesmo valor. Mostre também a
distribuição por tipo. A alteração de horário gera o aviso usado na próxima etapa.

## 6. Consultar e testar a restrição do Visualizador

**POST `/auth/login`** e substituir o token:

```json
{
  "email": "visualizador.demo@example.com",
  "senha": "DemoViaja123!"
}
```

| Chamada | Parâmetros | Resultado esperado |
| --- | --- | --- |
| GET `/viagens/{viagem_id}/destinos` | `viagem_id = 1` | `200`: consulta permitida |
| GET `/notificacoes` | Manter padrões | Localizar o aviso da alteração do horário |
| PATCH da ocorrência, abaixo | `viagem_id = 1`, `destino_id = 1`, `atividade_id = A` | `403`: alteração proibida |

No mesmo endpoint PATCH da etapa 5, envie:

```json
{
  "hora_inicio": "12:00:00"
}
```

A tentativa deve ser recusada. Consulte **GET `/viagens/1/destinos/1/atividades`**
e confira que a ocorrência A continua às **11h**.

Fala sugerida: “Os participantes compartilham o roteiro, mas as permissões são
verificadas em cada operação.”

## 7. Demonstrar isolamento de uma viagem privada

**POST `/auth/login`** e substituir o token:

```json
{
  "email": "externo.demo@example.com",
  "senha": "DemoViaja123!"
}
```

**GET `/viagens/{viagem_id}`**, com `viagem_id = 1`.

Resultado esperado: **404**, pois essa conta não participa da viagem.

## 8. Concluir a atividade e publicar uma avaliação

Faça login novamente como `criador.demo@example.com`, com senha `DemoViaja123!`,
e substitua o token em **Authorize**.

**PATCH `/viagens/{viagem_id}/destinos/{destino_id}/atividades/{atividade_id}`**

Parâmetros: `viagem_id = 1`, `destino_id = 1`, `atividade_id = A`.

```json
{
  "status": "concluida"
}
```

Mostre os campos que registram a realização. A conclusão é declarada pelo grupo,
não uma comprovação externa de presença.

**PUT `/viagens/{viagem_id}/destinos/{destino_id}/atividades/{atividade_id}/avaliacao`**

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
| GET `/catalogo/atividades/{atividade_id}/avaliacoes` | `atividade_id = 3`, `pagina = 1`, `tamanho_pagina = 20` |
| GET `/catalogo/atividades/{atividade_id}` | `atividade_id = 3` |

Aqui o ID é **3, do catálogo**, e não A, da ocorrência privada. Se o usuário já
avaliou Disney Springs, o PUT atualiza sua avaliação existente, sem duplicá-la.

## 9. Encerrar com os dados geográficos

**GET `/viagens/{viagem_id}/mapa`**, com `viagem_id = 1`.

Mostre Orlando e Miami, suas coordenadas e a ordem das paradas. O backend fornece
os pontos; a renderização do mapa pertence ao frontend.

Se houver tempo, consulte também **GET `/usuarios/me/paises-visitados`** e
**GET `/catalogo/destinos/ranking`**, mantendo os parâmetros padrão. Países
visitados dependem do status e da data de chegada, não apenas de existir uma parada.

## Ensaios e repetição

- Cada POST da etapa 4 cria outra ocorrência e soma seu custo. Para continuar o
  mesmo ensaio, reutilize A nas edições em vez de executar novamente o POST.
- Para remover apenas a ocorrência do ensaio, use **DELETE
  `/viagens/{viagem_id}/destinos/{destino_id}/atividades/{atividade_id}`**, como
  Criador ou Editor, com `viagem_id = 1`, `destino_id = 1`, `atividade_id = A`.
  Isso retira seu custo do orçamento, mas preserva a avaliação pública.
- Reiniciar a API não desfaz as alterações. O seed não sobrescreve os dados.
- Confira as contas, os IDs e as datas antes da apresentação. Não é necessário
  resetar o banco para executar este roteiro.

Referências: [seed](seed-demonstracao.md), [atividades](atividades-roteiro.md),
[orçamento](orcamento-viagem.md) e [avaliações](avaliacoes-atividades.md).
