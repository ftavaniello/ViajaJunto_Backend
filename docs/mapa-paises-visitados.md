# Países visitados e mapa do roteiro — RF11

O backend entrega os dados; desenhar o mapa, colorir países e posicionar marcadores
é responsabilidade do frontend (jsVectorMap para países, Leaflet/OSM ou similar para
o roteiro).

## Países visitados

`GET /usuarios/me/paises-visitados` — autenticado; retorna somente os dados do usuário
do token. Não existe rota para consultar os países de outra pessoa. Sem token: 401.

```json
{
  "total": 2,
  "paises": [
    {"pais_codigo": "BR", "primeira_visita": "2025-06-02",
     "ultima_visita": "2025-06-02", "total_viagens": 1},
    {"pais_codigo": "PT", "primeira_visita": "2025-06-05",
     "ultima_visita": "2026-01-10", "total_viagens": 2}
  ]
}
```

`pais_codigo` é ISO 3166-1 alfa-2 em maiúsculas, o mesmo código de região do
jsVectorMap (`selectedRegions: paises.map(p => p.pais_codigo)`). Cada país aparece
uma única vez, ordenado pelo código. Sem visitas, a resposta é `{"total": 0, "paises": []}`.

### Critério de visita efetiva

Uma parada do roteiro conta como visita do usuário quando, ao mesmo tempo:

1. o usuário participa da viagem — é o criador ou um colaborador (editor ou
   visualizador). Viagens compartilhadas contam para todos os participantes atuais;
   quem é removido da viagem deixa de contá-la;
2. a viagem está `confirmada` ou `concluida`. Viagens `planejando` são planos e não
   contam, mesmo com datas passadas;
3. a data de chegada da parada já chegou (`data_chegada <= hoje`, data UTC). Paradas
   futuras não contam, mesmo em viagem confirmada ou marcada como concluída.

O país é o do destino do catálogo da parada. Status de atividades não entram no
critério: a visita é ao destino, não depende de concluir atividades.
`primeira_visita` e `ultima_visita` são a menor e a maior data de chegada que
atendem ao critério naquele país; `total_viagens` conta viagens distintas.

A regra fica em `app/domain/paises_visitados.py`; o repositório só lista as paradas
das viagens do participante.

## Pontos do roteiro

`GET /viagens/{viagem_id}/mapa` — criador e colaboradores (qualquer papel). Sem
token: 401; viagem inexistente ou de que o usuário não participa: 404.

```json
{
  "viagem_id": 7,
  "paradas": [
    {"parada_id": 31, "destino_catalogo_id": 2, "ordem": 1, "nome": "Porto",
     "pais_codigo": "PT", "latitude": 41.1579, "longitude": -8.6291,
     "data_chegada": "2027-07-02", "data_saida": "2027-07-04"},
    {"parada_id": 30, "destino_catalogo_id": 1, "ordem": 2, "nome": "Lisboa",
     "pais_codigo": "PT", "latitude": 38.7223, "longitude": -9.1393,
     "data_chegada": "2027-07-05", "data_saida": "2027-07-08"}
  ]
}
```

- As paradas vêm na ordem de visita (`ordem`, depois `id`), a mesma de
  `GET /viagens/{viagem_id}/destinos`. Ligar os pontos nessa sequência desenha o roteiro.
- O mesmo destino pode aparecer mais de uma vez (revisita).
- Coordenadas são graus decimais (WGS 84) em **número** JSON, prontos para a
  biblioteca de mapas. Destinos do catálogo sem coordenadas vêm com `latitude` e
  `longitude` nulos: o frontend os lista, mas não os marca no mapa.
- Viagem sem paradas retorna `"paradas": []`.

Não há migração: países e coordenadas já estão em `destinos_catalogo`
(`pais_codigo`, `latitude`, `longitude`).
