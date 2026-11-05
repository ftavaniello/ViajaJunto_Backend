# Ranking público de destinos — RF25

`GET /catalogo/destinos/ranking?limite=10` — consulta pública, sem autenticação, para
destacar na página inicial os destinos mais bem avaliados. Não expõe dados de viagens
nem de quem avaliou.

## Origem da nota

Destinos não recebem avaliação própria (decisão D2): a nota de um destino agrega
**todas as avaliações das atividades do catálogo que pertencem a ele** (tabela
`avaliacoes`, ligada a `catalogo_atividades.destino_catalogo_id`). Avaliações de
contas excluídas continuam contando (D10). O registro de avaliações é da issue #23;
o ranking só lê a tabela.

## Ordenação

A ordem usa a média bayesiana, para que um destino com uma única nota 5 não fique
acima de outro com dezenas de notas altas:

```
nota_ranking = (m × C + soma_das_notas) / (m + total_avaliacoes)
```

- `C` (`media_geral`): média de todas as avaliações do catálogo;
- `m` (`peso_priori`): `RANKING_PESO_PRIORI = 5` em `app/domain/regras.py`.

Desempate estável, nesta ordem:

1. `nota_ranking` exata, decrescente (comparada sem arredondamento);
2. `total_avaliacoes`, decrescente;
3. `destino.id`, crescente.

A mesma base sempre produz a mesma ordem. Não há cache: uma nova avaliação muda o
ranking na próxima consulta.

## Destinos sem avaliação

Não aparecem. Se nenhum destino tem avaliação, a resposta é
`{"media_geral": null, "peso_priori": 5, "itens": []}` e o frontend pode
esconder a seção ou mostrar uma mensagem.

## Contrato

`limite`: inteiro de 1 a 50, padrão 10. Fora disso, 422.

```json
{
  "media_geral": 4.13,
  "peso_priori": 5,
  "itens": [
    {
      "posicao": 1,
      "destino": {"id": 1, "nome": "Lisboa", "pais_codigo": "PT", "categoria": "cidade",
                  "descricao": null, "latitude": "38.722300", "longitude": "-9.139300",
                  "foto_url": null, "id_externo": null, "fonte": "manual"},
      "media_avaliacoes": 4.6,
      "nota_ranking": 4.36,
      "total_avaliacoes": 5
    }
  ]
}
```

- `media_avaliacoes`: média simples das notas (1 a 5), duas casas — é a nota a exibir.
- `nota_ranking`: média bayesiana usada na ordenação, duas casas.
- Arredondamento meio para cima; a ordem considera os valores exatos.
- `destino` tem o mesmo formato de `GET /catalogo/destinos/{destino_id}`.

A regra fica em `app/domain/ranking_destinos.py`. O banco agrega contagem e soma por
destino em uma consulta; não há migração, porque `avaliacoes` e os índices em
`catalogo_atividade_id` e `destino_catalogo_id` já existem.


## Cache Redis

A rota pública retorna `X-Cache: MISS` quando consulta o PostgreSQL e preenche o
Redis; `HIT` quando reutiliza o snapshot; `BYPASS` quando o cache está indisponível
ou não foi possível gravar o snapshot. A resposta JSON mantém o mesmo contrato.
`Cache-Control: no-store` evita confundir esse cache interno com o do navegador.

O TTL é `CACHE_TTL_SECONDS` (60 segundos por padrão). Um snapshot com os primeiros
50 destinos atende a todos os valores de `limite`, sem recalcular a agregação SQL.
A média geral continua considerando todas as avaliações, não só o recorte retornado.
O cálculo e a ordenação exata permanecem no domínio.

- Dados: `viajajunto:ranking:destinos:v1`.
- Versão de invalidação: `viajajunto:ranking:destinos:v1:versao`.
- Publicar/atualizar uma avaliação ou importar o catálogo invalida após commit.
- Reset e criação efetiva do seed completo invalidam após a transação externa.
- Excluir conta ou viagem não exige invalidação: as avaliações são preservadas,
  e o ranking não expõe a autoria nem os dados privados do roteiro.
- Enriquecimento Geoapify preserva os destinos e vínculos existentes; atividades
  novas não têm avaliações, portanto não alteram esse ranking.

Uma versão impede que uma consulta iniciada antes da invalidação regrave um
snapshot obsoleto depois dela. Falhas no Redis não impedem consultas ou avaliações;
uma falha de invalidação pode manter o snapshot anterior até o TTL. Alterações
manuais no banco também só aparecem após expiração ou invalidação explícita.

### Demonstrar no Swagger

Na seção **Catálogo**, execute **GET `/catalogo/destinos/ranking`**, com `limite = 10`,
duas vezes em menos de 60 segundos. Observe **Response headers → x-cache**:
`MISS` seguido de `HIT` (a primeira pode ser `HIT` se já houver cache).

Para mostrar invalidação, aqueça o ranking, publique/atualize uma avaliação válida
pela API e consulte novamente: `MISS`, depois `HIT`. Não é necessário que a ordem
mude: a média pode arredondar para o mesmo valor e os demais destinos podem manter
suas posições. Se aparecer `BYPASS`, confira MiniStack, o provisionamento AWS CLI
e o Redis em [infra/README.md](../infra/README.md).
