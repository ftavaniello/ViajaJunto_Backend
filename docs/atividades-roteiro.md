# Atividades do roteiro — issue #24

Implementa RF12–RF14 e a persistência dos custos previstos do RF16. Uma atividade
planejada é uma ocorrência de uma atividade do catálogo dentro de uma parada da
viagem. Os dados públicos (nome, foto, categoria, descrição e local) são reutilizados,
e data, horário, duração, custo e status pertencem somente ao planejamento.

## Rotas autenticadas

Prefixo: `/viagens/{viagem_id}/destinos/{destino_id}/atividades`.

| Método e sufixo | Operação | Quem pode |
|---|---|---|
| GET no prefixo | Lista cronologicamente | Criador, Editor e Visualizador |
| POST no prefixo | Adiciona atividade do catálogo | Criador e Editor |
| GET `/{atividade_id}` | Consulta ocorrência | Criador, Editor e Visualizador |
| PATCH `/{atividade_id}` | Edita planejamento | Criador e Editor |
| DELETE `/{atividade_id}` | Remove ocorrência | Criador e Editor |

Todos exigem token JWT. O usuário é identificado pelo token; não se aceita autor,
criador ou comprovação no corpo. Visitante recebe 401; Visualizador tentando editar,
403. Usuário sem vínculo com a viagem recebe 404. Viagem, parada e atividade precisam
corresponder entre si, mesmo quando o usuário tem acesso a mais de uma viagem.
Não é permitido usar uma atividade do catálogo pertencente a outro destino.

O POST recebe `catalogo_atividade_id`; o `atividade_id` das demais operações é o ID
privado retornado pelo POST. Uma mesma atividade do catálogo pode ser programada
mais de uma vez, em ocorrências independentes. Não há operação para mover uma
ocorrência de parada ou trocar sua referência de catálogo pelo PATCH.

## Dados e validações

```json
{
  "catalogo_atividade_id": 1,
  "data": "2027-07-03",
  "hora_inicio": "09:00:00",
  "duracao_minutos": 90,
  "custo_previsto": "25.50",
  "status": "pendente"
}
```

A data é obrigatória e deve estar entre a chegada e a saída da parada, inclusive.
O horário é local, sem fuso; pode ser omitido. Duração é opcional, mas, quando
informada, deve ser um inteiro positivo de minutos, até o limite INTEGER do banco.
A duração é estimativa: não há validação de sobreposição de atividades nem cálculo
de um horário final para restringir a estadia. A validação temporal usa a data agendada.

O custo padrão é zero. Usa `Decimal` no domínio e NUMERIC(12,2) no PostgreSQL,
não aceita valores negativos, não finitos, acima de 9.999.999.999,99 ou com mais de
duas casas decimais significativas. Para representar decimais com precisão no JSON,
prefira strings como `"25.50"`; as respostas devolvem esse formato, com duas casas.
Os valores estão na moeda da viagem (BRL por padrão no banco), sem conversão cambial.
O resumo financeiro será implementado na #25; não há total agregado persistido
ou cache de orçamento para atualizar nesta entrega.

A resposta contém IDs de viagem/parada/catálogo/ocorrência, o objeto `atividade`
com os dados públicos descritivos, o planejamento e `realizada_em`/`realizada_por_id`.
Nenhuma alteração muda o catálogo público.

## Ordem cronológica

A listagem retorna uma lista por data crescente; em cada dia, primeiro as atividades
com horário crescente e depois as sem horário. O ID desempata horários iguais.
Não há paginação da agenda de uma parada. Uma parada sem atividades retorna `[]`.
As leituras usam uma consulta com os dados do catálogo, sem consulta extra por item.

## PATCH e status

- Campos omitidos permanecem inalterados.
- `hora_inicio: null` e `duracao_minutos: null` removem esses dados opcionais.
- Data, custo e status nulos permanecem inalterados; para zerar custo, envie `"0.00"`.
- As entradas de status são `pendente`, `confirmada` e `concluida`; novas atividades
  começam como `pendente`, salvo se outro desses status for informado.
- Ao concluir, o servidor grava o usuário autenticado e o instante UTC. A conclusão
  pode ser indicada no POST ou PATCH. Não se infere conclusão apenas pela passagem
  da data, nem se afirma comprovação externa de presença nesta issue.
- Editar outros campos de uma ocorrência já concluída preserva quem concluiu e quando.
  Reabrir como pendente/confirmada limpa a comprovação atual; concluir novamente
  registra o novo responsável e instante. As transições entre os três status são livres.

A regra da #19 também protege atividades: reduzir o período de uma parada é recusado
se alguma atividade ficar fora dele. Alterações no planejamento usam o mesmo bloqueio
da viagem e a mesma UnitOfWork, evitando disputa com a edição das datas do roteiro.

Regras de vínculo/data/horário retornam 400; formatos, duração/custo fora dos limites,
status de entrada inválido e campos desconhecidos retornam 422. Recursos inexistentes
ou fora do contexto retornam 404.

## Migração e registros legados

A revisão `b5e0f3a72c91` converte `planejada` em `pendente` e `realizada` em `concluida`,
preservando IDs, custos, datas, vínculos e campos de comprovação. Acrescenta suporte
a `confirmada` e atualiza as restrições/default de status.

`cancelada` é preservado somente como estado legado: pode aparecer nas respostas,
mas não é aceito no POST/PATCH como novo status. Um operador autorizado pode
replanejar a ocorrência legada informando um dos três estados novos; editar custo,
horário ou data sem informar status mantém o cancelamento. Não se reativa nenhum
cancelamento automaticamente. Essa foi a opção adotada para evitar perda de significado
nos registros antigos; se a equipe preferir outro tratamento, deve defini-lo explicitamente.

O histórico anterior tinha duas pontas com adição repetida de `usuarios.criado_em`.
A revisão nova une ambas. As adições existentes da coluna compartilhada agora usam
`IF NOT EXISTS`; o downgrade da revisão redundante não apaga a coluna da outra linha.
Não foram removidas revisões, tabelas ou dados de usuários. O histórico completo foi
testado em schema vazio e no caminho de atualização da base existente.

Um downgrade converte os estados pendente e confirmada em planejada, pois a versão
anterior não distingue confirmação; concluida volta a realizada e cancelada é preservada.
Use downgrade somente com avaliação do impacto dessa perda de distinção.

## Exclusão e testes

Excluir uma ocorrência remove apenas a atividade do roteiro. O catálogo e as avaliações
públicas permanecem; a referência de comprovação da avaliação à ocorrência excluída
fica nula, conforme as FKs existentes. Os endpoints de avaliações pertencem à #26.
Falhas de persistência desfazem integralmente criação, edição e exclusão.

Para testar no Swagger:

1. Atualize a API com `docker compose up -d --build api` para aplicar as migrações.
2. Autentique-se e use **Authorize**.
3. Crie uma viagem e uma parada via operações da #19; anote os IDs privados.
4. Consulte `/catalogo/atividades` e selecione uma atividade do mesmo destino da parada.
5. Use o POST com uma data dentro da estadia e os IDs corretos.
6. Consulte a lista; teste horários iguais, sem horário, custos e mudanças de status.
7. Repita com Visualizador para verificar leitura e bloqueio de escrita.

O seed existente abastece apenas os catálogos. Não cria viagens, paradas ou atividades
privadas automaticamente. Testes usam PostgreSQL exclusivo e cobrem também operações
com IDs cruzados, migração, estados legados e rollback após gravação.
