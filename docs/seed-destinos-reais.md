# Seed de destinos reais

O seed completo contém Orlando, Miami, Rio de Janeiro e Roma. Os nomes dos lugares
são reais; viagens, hospedagens, custos, durações e reviews são exemplos fictícios.
O banco não contém prefixos como `Demo` nos nomes exibidos.

## Conteúdo

| Roteiro | Dono e acesso | Destinos | Orçamento de exemplo |
|---|---|---|---|
| `Orlando e Miami em grupo` | Criador, editor e visualizador | Orlando e Miami | BRL 6.000 |
| `Cultura e paisagens no Rio de Janeiro` | Criador | Rio de Janeiro | BRL 1.200 |
| `História e gastronomia em Roma` | Criador | Roma | BRL 2.000 |
| `Roma: roteiro privado` | Externo | Roma | BRL 500 |

Os roteiros preenchidos usam quatro destinos, 24 atividades públicas, cinco viagens,
seis paradas, 36 ocorrências privadas e 20 avaliações fictícias. A quinta viagem,
“Rio para descansar”, pertence à conta descartável. Existem ainda 22 viagens vazias
para testar criação de roteiro e paginação, totalizando 27 viagens. As ocorrências incluem os três
status de atividade. O orçamento privado de Roma fica abaixo do custo planejado,
para testar orçamento excedido; os outros limites permitem testar saldo disponível.
Todos os valores são ilustrativos em BRL, a moeda atual das viagens, inclusive
nos roteiros internacionais. O Metromover tem custo previsto zero.

- **Orlando:** Magic Kingdom Park, Universal Studios Florida, Disney Springs,
  ICON Park, East End Market e Lake Eola Park. A referência inclui a região
  turística de Orlando, como Lake Buena Vista.
- **Miami:** Vizcaya Museum and Gardens, South Beach, Bayside Marketplace,
  Metromover, Versailles Restaurant e Bayfront Park. South Beach fica em Miami Beach.
- **Rio:** Cristo Redentor, Pão de Açúcar, Feira Hippie de Ipanema,
  Confeitaria Colombo, Bonde de Santa Teresa e Jardim Botânico do Rio de Janeiro.
- **Roma:** Coliseu, Fontana di Trevi, Via del Corso, Trastevere, Metrô de Roma
  e Villa Borghese. Trastevere representa um passeio gastronômico pelo bairro.

As coordenadas são referências aproximadas dos centros das cidades; não representam
as entradas das atrações. Os horários e períodos não verificam calendário real de
abertura ou disponibilidade. Fotos continuam sem preenchimento nesta carga.
Os reviews são fictícios e criados pelas mesmas regras da API, somente
para ocorrências concluídas e participantes das viagens. Há exemplos com mais de
um autor e médias diferentes para testar a busca por nota mínima.

## Como carregar e encontrar

No Docker Compose de desenvolvimento, a carga adicional roda automaticamente
antes da API, junto ao seed completo. Para aplicá-la imediatamente:

```powershell
docker compose exec api python -m app.adapters.inbound.cli.seed_demo --completo
```

O manifesto impresso contém IDs reais agrupados em
`destinos_catalogo`, `atividades_catalogo`, `viagens`, `paradas`, `atividades_roteiro`
e `avaliacoes`. Exemplos: `viagens.florida` e
`atividades_catalogo.orlando-1` (Magic Kingdom Park).

No Swagger:

1. Faça login como `criador.demo@example.com` / `DemoViaja123!`.
2. Em `GET /viagens`, procure “Orlando e Miami em grupo”, “Cultura e paisagens no Rio de Janeiro” ou “História e gastronomia em Roma”.
3. Liste destinos e atividades da viagem escolhida para consultar agenda e custos.
4. Consulte `/catalogo/destinos?nome=Orlando` ou `?pais_codigo=US`, e use
   `destino_catalogo_id` no catálogo de atividades para filtrar por cidade.
5. Abra os detalhes do Magic Kingdom Park, Vizcaya, Cristo Redentor e Coliseu
   para ver avaliações; use `nota_minima` para comparar os resultados.
6. Entre como editor/visualizador para testar a viagem da Flórida, ou como externo
   para consultar a Roma privada. As demais contas não têm acesso a essa viagem.
7. Consulte o resumo financeiro das viagens para ver limites, saldo e excesso.

## Banco novo e reexecução

A carga única `dados-iniciais-v2` substitui as duas cargas anteriores. Uma base nova
recebe apenas os quatro destinos, sem destinos genéricos ou nomes com prefixos.
Bancos com a versão antiga precisam do [reset explícito](reset-banco.md);
o seed não remove dados sozinho. Veja [o guia principal](seed-demonstracao.md) para contas, totais e execução.
Depois da primeira carga, repetir preserva edições e exclusões, sem duplicar dados.

## Referências da curadoria

Consultadas em 03/11/2026, para nomes e descrições gerais, sem coletar imagens:

- [Visit Orlando: Disney Springs e East End Market](https://www.visitorlando.com/things-to-do/theme-parks/walt-disney-world-resort/disney-springs/).
- [Visit Orlando: atrações da região](https://www.visitorlando.com/blog/post/holiday-season-orlando/).
- [Greater Miami: Bayfront Park e Bayside](https://www.miamiandbeaches.com/l/outdoor-experiences/bayfront-park/2443).
- [Miami-Dade: Metromover](https://www.miamidade.gov/global/transportation/metromover.page).
- [Prefeitura do Rio: pontos turísticos](https://controladoria.prefeitura.rio/pontos-turisticos/).
- [Turismo Roma: roteiro pelo Coliseu, Trevi e Villa Borghese](https://turismoroma.it/it/itinerari/roma-72-ore).
