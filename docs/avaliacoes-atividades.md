# Avaliações de atividades — issue #26

Implementa RF22–24 e RN01. A RN05 é interpretada conforme o modelo já adotado:
a avaliação pertence à **atividade do catálogo**, não diretamente ao destino.
Ranking de destinos continua sendo outro caso de uso. Fotos continuam como
referências em `foto_url`; esta entrega não implementa upload nem hospedagem.

## Realização e participação

Para publicar ou substituir uma avaliação, o usuário precisa:

1. Estar autenticado e participar atualmente da viagem como criador, editor ou visualizador.
2. Informar uma atividade que pertença exatamente à viagem e à parada da URL.
3. Ter essa ocorrência marcada como `concluida`, com `realizada_em` preenchido.

A conclusão é a declaração compartilhada do grupo já usada pelo roteiro. O campo
`realizada_por_id` indica quem registrou a conclusão, não todos os participantes;
um visualizador pode avaliar uma ocorrência concluída por outro participante.
Não há comprovação externa de presença nem restrição adicional baseada no dia atual.
O mesmo lock da viagem protege publicação contra reabertura/exclusão da ocorrência.
As permissões são revalidadas depois de adquirir o lock.

Usuário sem participação recebe 404, preservando a privacidade da viagem. Participante
com atividade pendente, confirmada ou cancelada recebe 403. Visitante recebe 401
na publicação e pode consultar normalmente os dados públicos.

## Publicar ou atualizar

```http
PUT /viagens/{viagem_id}/destinos/{destino_id}/atividades/{atividade_id}/avaliacao
Authorization: Bearer <token>
Content-Type: application/json
```

```json
{
  "nota": 5,
  "comentario": "Gostei da visita."
}
```

`atividade_id` é o ID **da ocorrência privada do roteiro**, não o ID do catálogo.
A nota é obrigatória, inteira de 1 a 5. Booleanos, strings e números fracionários
são recusados. Comentário opcional, até 2.000 caracteres, com espaços externos
removidos; vazio equivale a nulo. Campos extras são recusados. A identidade vem
do JWT, nunca do corpo da requisição.

Há uma avaliação por usuário e atividade do catálogo, inclusive entre ocorrências,
paradas e viagens diferentes. O PUT retorna 200 tanto na criação quanto na atualização.
Reenviar atualiza nota, comentário e referência à ocorrência válida, preservando ID
e data de criação. Comentário omitido/nulo remove o anterior: PUT substitui a avaliação.
A unicidade e o upsert do PostgreSQL também protegem publicações simultâneas.

A resposta contém somente `id`, `nota`, `comentario`, `autor_nome` e `criado_em`.
Não inclui email, ID do usuário, viagem, estadia, custos ou comprovantes privados.

## Consultas públicas

### Detalhe e resumo

`GET /catalogo/atividades/{atividade_id}` conserva os dados descritivos e `foto_url`
e agora informa:

```json
{
  "avaliacoes_disponiveis": true,
  "media_avaliacoes": null,
  "total_avaliacoes": 0,
  "reviews": []
}
```

O trecho ilustra os campos; no detalhe, `reviews` contém até 20 avaliações mais
recentes, ordenadas por `criado_em` e ID decrescentes. O total e a média consideram
**todas** as avaliações, não apenas as primeiras 20. Sem avaliações: média nula,
total zero e lista vazia. `avaliacoes_disponiveis=true` indica que o recurso está
implementado, mesmo quando a atividade ainda não recebeu avaliações.

A listagem `/catalogo/atividades` inclui a mesma média e total por item; o campo
`reviews` fica vazio nessa listagem. Isso evita carregar comentários para todos
os resultados de busca. As médias são calculadas por agregação no banco, sem
coluna de média armazenada ou consulta adicional por item.

### Reviews paginados

```http
GET /catalogo/atividades/{atividade_id}/avaliacoes?pagina=1&tamanho_pagina=20
```

Resposta: `itens`, `pagina`, `tamanho_pagina` e `tem_proxima`. Página mínima 1;
tamanho entre 1 e 100. Atividade existente sem reviews retorna lista vazia;
atividade inexistente retorna 404. Alterações entre requisições podem mudar páginas.

### Nota mínima

```http
GET /catalogo/atividades?nota_minima=4.5&categoria=cultura&localizacao=Lisboa
```

Aceita número finito entre 1 e 5, inclusive fracionário. Combina com os demais
filtros por E. Compara inclusivamente com a média sem arredondamento prévio,
antes de paginar, e mantém a ordenação por ID. Atividades sem avaliações não
atendem a uma nota mínima. Sem esse filtro, elas continuam aparecendo.

## Efeitos das alterações e exclusões

Uma avaliação já publicada permanece se a ocorrência for reaberta, se o membro sair
ou se a viagem/ocorrência for excluída. Uma nova publicação/substituição exige novamente
participação e uma ocorrência concluída. Se a ocorrência original não existir mais,
a avaliação pode ser substituída por meio de outra ocorrência elegível da mesma atividade.

Excluir a conta preserva nota/comentário e torna `autor_nome` nulo. Essas avaliações
continuam contando na média. O banco já possui os vínculos `ON DELETE SET NULL` e
a restrição de unicidade necessários; não foi criada nova migração para a issue #26.
A exclusão de conta limpa antes a referência do responsável pela conclusão, dentro
da mesma transação, evitando conflito com a remoção em cascata do roteiro.

## Testar pelo Swagger com o seed

1. Faça login como `criador.demo@example.com`, senha `DemoViaja123!`, e use **Authorize**.
2. Em `GET /viagens`, escolha `[Demo] passada` ou `[Demo] compartilhada`.
3. Liste os destinos e atividades. Copie os IDs da viagem, parada e de uma ocorrência
   com `status=concluida` para o PUT da tag **Avaliações**.
4. Envie nota/comentário. Consulte o detalhe público pelo `catalogo_atividade_id`
   daquela ocorrência. A média, o total e seu review devem aparecer sem autenticação.
5. Reenvie outra nota como a mesma conta: o total não aumenta e a média muda.
6. Na viagem compartilhada, entre como `visualizador.demo@example.com` com a mesma
   senha e publique outra nota. O total passa a dois. Teste também como externo,
   sem token e usando uma ocorrência pendente.
7. Pesquise `/catalogo/atividades?nota_minima=4` e confira os resultados.

Os seeds existentes não são reexecutados ou sobrescritos por esta entrega. Os exemplos
já contêm ocorrências concluídas para publicar avaliações pelos fluxos reais da API.
