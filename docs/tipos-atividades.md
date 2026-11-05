# Tipos de atividades do documento original

O domínio e a API adotam os cinco tipos especificados pelos criadores do projeto:
`passeio`, `refeicao`, `hospedagem`, `transporte` e `outro`.
Na API os valores usam minúsculas sem acentos; os nomes do enum são PASSEIO,
REFEICAO, HOSPEDAGEM, TRANSPORTE e OUTRO. O campo permanece `categoria`.
As categorias de destinos (`cidade`, `praia`, `natureza`, `cultural`) são independentes.

## Banco existente

A revisão Alembic `f8c2d6e41b90` converte apenas a categoria das atividades:

| Categoria antiga | Tipo atual |
| --- | --- |
| `cultura`, `lazer` | `passeio` |
| `alimentacao` | `refeicao` |
| `transporte` | `transporte` |
| `compras`, `outros` | `outro` |

Não apaga registros nem muda IDs, vínculos de roteiro, custos ou avaliações.
Não recria o banco e não executa novamente o seed. O seed novo já usa esses tipos.
O resumo financeiro passa a retornar cinco grupos; valores das categorias unificadas
são somados, mantendo o total planejado e o saldo. Filtros e lotes novos devem usar
os valores atuais; valores antigos retornam erro de validação, não são aliases.

Aplique com `alembic upgrade head` no ambiente da API. O Compose já aplica as
migrações no início do serviço; reiniciar/recriar o serviço executa esse fluxo.
Esta alteração foi validada no banco de testes e aplicada ao banco local de
desenvolvimento. Uma verificação na mesma transação confirmou que somente as
categorias mudaram; contas, viagens, participações, roteiros, custos, avaliações
e os demais dados do catálogo foram preservados. A API local já expõe os cinco tipos.

O downgrade mantém registros, mas não recupera distinções que foram unificadas:
`passeio` volta para `cultura`, `refeicao` para `alimentacao`, `hospedagem` e `outro`
para `outros`, e `transporte` permanece. Não use downgrade para recuperar a
classificação original exata; a conversão muitos-para-um perde essa distinção.

## Hospedagem

Pode ser importada no catálogo com `categoria: "hospedagem"` ou buscada com:

```bash
python -m app.adapters.inbound.cli.enriquecer_catalogo --destino 1 --categoria hospedagem
```

O adaptador usa a categoria oficial `accommodation` do
[Geoapify](https://apidocs.geoapify.com/docs/places/). É catálogo de locais, sem
reservas ou pagamentos. Uma hospedagem cadastrada pode entrar no roteiro como
qualquer atividade, com datas, custo e status, e participa do resumo financeiro.
O campo livre `hospedagem` da parada continua disponível para anotações.
