# Orçamento da viagem — RF15 a RF17

Cada viagem tem um orçamento total único (RF15). Os custos previstos (RF16) são o
campo `custo_previsto` das atividades do roteiro (ver
[atividades-roteiro.md](atividades-roteiro.md)). O resumo financeiro (RF17) combina os dois.

## Rotas autenticadas

Prefixo: `/viagens/{viagem_id}/orcamento`.

| Método | Operação | Quem pode |
|---|---|---|
| GET | Consulta o resumo financeiro | Criador, Editor e Visualizador |
| PUT | Define ou substitui o orçamento total e retorna o resumo | Criador e Editor |

Visitante recebe 401; Visualizador tentando editar, 403; usuário sem vínculo com a
viagem ou viagem inexistente, 404. Corpo inválido (ausente, nulo, negativo, não finito,
acima de 9.999.999.999,99, com mais de duas casas ou com campos extras) recebe 422.

```json
PUT /viagens/1/orcamento
{ "valor_total": "1000.00" }
```

O valor usa `Decimal` no domínio e NUMERIC(12,2) no PostgreSQL (tabela `orcamentos`,
com `viagem_id` único), na moeda da viagem, sem conversão cambial. Enviar outro valor
substitui o anterior; zero é um orçamento válido. Não há migração nesta entrega: a
tabela já existia desde `a3f1c9d27b45`. Uma linha com `limite_total` nulo equivale a
orçamento não definido.

## Resumo financeiro

```json
{
  "viagem_id": 1,
  "orcamento_total": "1000.00",
  "total_planejado": "300.00",
  "saldo_disponivel": "700.00",
  "percentual_consumido": "30.00",
  "orcamento_excedido": false,
  "categorias": [
    {"categoria": "passeio", "total_planejado": "200.00",
     "percentual_orcamento": "20.00", "percentual_planejado": "66.67"},
    {"categoria": "refeicao", "total_planejado": "0.00",
     "percentual_orcamento": "0.00", "percentual_planejado": "0.00"},
    {"categoria": "hospedagem", "total_planejado": "100.00",
     "percentual_orcamento": "10.00", "percentual_planejado": "33.33"}
  ]
}
```

(As categorias `transporte` e `outro` foram omitidas do exemplo; a
resposta sempre traz as cinco, na ordem do enum, mesmo zeradas.)

### Fórmula

- **Total planejado**: soma de `custo_previsto` de todas as atividades da viagem,
  em qualquer parada e status, exceto `cancelada` (status legado, só leitura).
- **Saldo disponível**: `orçamento total − total planejado`. Fica negativo quando o
  orçamento estoura, e `orcamento_excedido` passa a `true`. Gastar exatamente o
  orçamento não é estouro.
- **Percentuais** (escala 0–100):
  - `percentual_consumido` = total planejado / orçamento total;
  - `percentual_orcamento` (por categoria) = custo da categoria / orçamento total —
    é o "percentual consumido por categoria" do RF17 e pode passar de 100;
  - `percentual_planejado` (por categoria) = custo da categoria / total planejado —
    a fatia da categoria dentro do planejado.

  Denominador escolhido: o **orçamento total**, que é o que o RF17 descreve como
  "consumido". A participação sobre o total planejado também é retornada para que
  o frontend possa mostrar a distribuição dos gastos sem fazer contas. Se o time
  combinar outro denominador, basta mudar `ResumoFinanceiro.calcular`.

### Arredondamento e casos-limite

- Valores monetários têm sempre duas casas. Somas e saldos são exatos em `Decimal`.
- Percentuais são calculados a partir dos valores exatos e arredondados para duas
  casas, meio-para-cima (`0,125` → `0,13`). Por isso a soma das participações pode
  diferir de 100,00 em centésimos (ex.: 33,33 + 66,67 = 100,00, mas 3 × 33,33 = 99,99).
- **Sem orçamento definido**: `orcamento_total`, `saldo_disponivel`,
  `percentual_consumido` e `percentual_orcamento` são `null`; o total planejado e
  as participações continuam disponíveis.
- **Orçamento zero**: percentuais sobre o orçamento são `null` (não há divisão por
  zero); o saldo é `−total planejado` e há estouro se houver qualquer custo.
- **Sem atividades**: total planejado `0.00`, saldo igual ao orçamento,
  `percentual_consumido` `0.00` e `percentual_planejado` `null` em todas as categorias.

### Consistência

Nenhum total é persistido: o resumo soma as atividades na consulta (uma única
agregação `GROUP BY` categoria no banco). Por isso, incluir, editar ou remover uma
atividade — inclusive excluir uma parada, que remove suas atividades — reflete no
próximo GET, sem totais desatualizados. O PUT retorna o resumo lido na mesma
transação em que gravou o orçamento.
