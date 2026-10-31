# Destinos e ordem de visita no roteiro — issue #19

Os destinos públicos de `/catalogo/destinos` são reutilizáveis. Uma parada do roteiro
é uma associação desses dados a uma viagem, com datas, descrição particular,
hospedagem e posição de visita. É permitido revisitar o mesmo destino em paradas
diferentes, cada uma com seu próprio ID.

## Operações e permissões

Todas exigem `Authorization: Bearer <token>` e identificam o usuário pelo token.
O corpo não aceita usuário, criador ou viagem como prova de autorização.

| Método e rota | Operação | Quem pode |
|---|---|---|
| `GET /viagens/{viagem_id}/destinos` | Lista por ordem de visita | Criador, Editor e Visualizador |
| `GET /viagens/{viagem_id}/destinos/{destino_id}` | Consulta uma parada | Criador, Editor e Visualizador |
| `POST /viagens/{viagem_id}/destinos` | Insere parada do catálogo | Criador e Editor |
| `PATCH /viagens/{viagem_id}/destinos/{destino_id}` | Altera estadia e texto particular | Criador e Editor |
| `PUT /viagens/{viagem_id}/destinos/ordem` | Define nova ordem completa | Criador e Editor |
| `DELETE /viagens/{viagem_id}/destinos/{destino_id}` | Exclui parada e suas atividades | Criador e Editor |

Os IDs usados como `destino_id` são das **paradas**, retornados pelo POST, e não do
catálogo. O POST recebe `destino_catalogo_id`, obtido na consulta pública.
A resposta traz os dois identificadores e o objeto `destino` com nome, país,
categoria, descrição pública, foto e coordenadas. O campo `descricao` na raiz
é particular desta parada e é persistido na coluna existente `observacoes`.

Leitura do roteiro completo não é paginada: retorna uma lista por `ordem` e `id`.
Uma viagem sem paradas retorna `[]`. Visitantes recebem 401; participantes sem
permissão de edição recebem 403. Quem não pertence à viagem recebe 404. Uma parada
inexistente ou de outra viagem também recebe 404, mesmo se o usuário tiver acesso
às duas viagens. A remoção de membro afeta as próximas requisições.

## Datas e campos particulares

Decisões adotadas para tornar o contrato da issue preciso:

- Chegada e saída são datas obrigatórias, sem horário/fuso; saída não pode anteceder chegada.
- O período deve ficar dentro de `data_inicio` e `data_fim` da viagem, inclusive os limites.
- Uma estadia de um único dia é válida. Sobreposição entre destinos é permitida;
  os requisitos não impõem exclusividade de dias. A ordem de visita é explícita e
  não é recalculada pelas datas.
- Alterar o período da viagem é bloqueado se alguma parada ficar fora dele.
- Alterar o período da parada é bloqueado se deixar atividades existentes fora dele.
- No PATCH, campos omitidos ou nulos permanecem inalterados. Texto vazio remove
  descrição ou hospedagem. Não se muda o destino do catálogo pelo PATCH.
- Nenhuma edição do roteiro altera nome, foto, categoria ou descrição do catálogo público.

Descrição tem limite de 10.000 caracteres e hospedagem de 255. Erros de regra,
como período invertido ou posição impossível, retornam 400; erros de formato,
campos desconhecidos e IDs não positivos retornam 422. Catálogo inexistente retorna 404.

## Ordem e transações

Ao inserir, `ordem` é opcional: omitida, adiciona ao fim. Se informada, deve estar
entre 1 e quantidade atual + 1. As posições seguintes são deslocadas.
O PUT recebe todos os IDs das paradas da viagem, exatamente uma vez:

```json
{"destinos_ids": [12, 10, 11]}
```

O primeiro fica com ordem 1, o segundo com 2 e assim por diante. IDs repetidos,
ausentes ou de outra viagem retornam 400 sem alterar o roteiro. Em roteiro vazio,
`{"destinos_ids": []}` é válido. Excluir uma parada compacta as posições restantes.

Inserção, edição, exclusão e reordenação usam uma única UnitOfWork. O adaptador
PostgreSQL bloqueia a linha da viagem durante a alteração para serializar operações
concorrentes do roteiro e mudanças de período. A restrição de unicidade da ordem
já é adiada até o fim da transação, permitindo trocar posições sem conflito
intermediário. Uma falha de persistência desfaz toda a operação.

## Exclusão com atividades

A política segue explicitamente as chaves estrangeiras existentes: excluir uma
parada remove, por cascata, suas atividades de planejamento. Catálogos públicos e
avaliações são preservados; a referência de comprovação da avaliação à atividade
removida se torna nula, como já previsto pelo modelo. Não há criação de avaliações
nesta issue. A resposta de exclusão é 204 e o frontend deve explicar esse efeito
antes de solicitar a operação.

Não foi necessária migração: `destinos_viagem`, `atividades_viagem`, seus campos,
a cascata e a restrição adiada de ordem já existem.

## Teste pelo Swagger

1. Abra `/docs`, autentique-se e use **Authorize**.
2. Crie uma viagem e anote seu ID e período.
3. Consulte `/catalogo/destinos` e escolha um `id` do catálogo.
4. No POST do roteiro, use o ID da viagem na URL e um corpo como:

```json
{
  "destino_catalogo_id": 1,
  "data_chegada": "2027-07-02",
  "data_saida": "2027-07-05",
  "descricao": "Nossa primeira parada",
  "hospedagem": "Hotel do grupo"
}
```

As datas do exemplo pressupõem uma viagem que inclua esse período; ajuste os IDs
e as datas aos seus dados. Repita o POST para outra parada, teste `ordem: 1`,
consulte a lista e use os IDs das paradas no PUT de reordenação. O PATCH pode alterar
a descrição particular; uma nova consulta ao catálogo deve continuar igual.

Para testar colaboração, use uma conta com vínculo de Editor ou Visualizador.
O fluxo de convites pertence à #16; os testes automatizados preparam os vínculos
no banco exclusivo de testes. O seed abastece somente o catálogo, nunca cria
viagens ou roteiros privados automaticamente.
