# Catálogo público de destinos — issue #18

Atende à pesquisa de destinos reutilizáveis (RF10/RN01) e aos dados gerais do RF09.
Datas de chegada e saída, ordem de visita e descrição particular pertencem ao roteiro
na issue #19; consultar ou importar o catálogo não altera o planejamento de viagens.

## Contrato público

- `GET /catalogo/destinos`: pesquisa paginada, sem login.
- `GET /catalogo/destinos/{destino_id}`: detalhe público, sem login.

Cada destino retorna `id`, `nome`, `pais_codigo`, `categoria`, `descricao`,
`latitude`, `longitude`, `foto_url` e `google_place_id`. Foto é uma referência HTTP/HTTPS;
não há upload ou download de imagens pelo backend. Descrição, coordenadas, foto e
referência externa podem ser nulas. Não são retornados usuários, convites, membros,
datas, custos ou outros dados privados de viagem.

| Filtro | Comportamento |
|---|---|
| `nome` | Trecho do nome, sem distinguir caixa; espaços externos são removidos |
| `pais_codigo` | Código de duas letras, por exemplo BR ou PT; aceita minúsculas |
| `categoria` | `cidade`, `praia`, `natureza` ou `cultural` |
| `pagina` | Inteiro a partir de 1; padrão 1 |
| `tamanho_pagina` | Inteiro entre 1 e 100; padrão 20 |

Os filtros são combinados por E. A busca não remove acentos, e `%` e `_` são literais,
não curingas. Nome vazio equivale a filtro ausente. Parâmetros desconhecidos e valores
inválidos retornam 422. ID inexistente retorna 404; ID não positivo retorna 422.
A consulta por país valida o formato alfa-2; não consulta um serviço externo de países.

Exemplo: `/catalogo/destinos?nome=lisboa&pais_codigo=pt&categoria=cidade`.

A resposta contém `itens`, `pagina`, `tamanho_pagina` e `tem_proxima`, em ordem crescente
por ID. Sem resultados ou além da última página, retorna `itens=[]` e
`tem_proxima=false`. A paginação é por deslocamento; alterações entre consultas podem
mudar as páginas. O ID retornado permitirá selecionar o destino ao montar um roteiro.

## Persistência e compatibilidade

A migração `a4d9e2f61b80` adiciona `categoria` e `descricao` a `destinos_catalogo`.
Registros existentes são preservados, recebem categoria `cidade` e descrição nula.
O banco exige uma das quatro categorias. Nome e país continuam obrigatórios;
latitude varia de -90 a 90 e longitude de -180 a 180. A entidade também valida os
valores antes de gravar, além do formato HTTP/HTTPS da foto.

As respostas de atividades continuam disponíveis e passam a incluir categoria e
descrição no objeto `destino` associado. Não há mudança nos IDs e vínculos existentes.

## Origem, seed e manutenção

A origem atual é curadoria manual pela equipe operadora, pelo mesmo importador
transacional de [atividades](catalogo-atividades.md). Somente quem tem acesso operacional
ao ambiente e ao banco pode abastecer. Não há POST, PATCH ou DELETE públicos para o
catálogo; um token de usuário comum não autoriza sua manutenção.

O seed do Compose de desenvolvimento usa `catalogo-exemplo.json`, agora com categoria
e descrição do destino. Continua rodando somente quando não há nenhum destino ou
atividade no catálogo. Reiniciar não duplica nem sobrescreve registros. Em bases já
abastecidas, a migração preenche apenas os campos novos; o seed não altera descrições.
Desative com `SEED_CATALOGO=false`. Fora do Compose, não há seed automático.

A integração Google Places não faz parte desta issue. `google_place_id` é somente
uma referência opcional e única; não implica enriquecimento automático.

O importador agora aceita lotes **somente de destinos**, sem exigir atividades:

```json
{
  "destinos": {
    "praia-exemplo": {
      "nome": "Praia de demonstração",
      "pais_codigo": "BR",
      "categoria": "praia",
      "descricao": "Registro fictício para desenvolvimento.",
      "latitude": "-27.500000",
      "longitude": "-48.500000",
      "foto_url": null
    }
  }
}
```

Salve o lote em um arquivo próprio e envie o JSON pela entrada padrão, sem fornecer
um caminho ao importador. No PowerShell com o Compose:

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new()
Get-Content -Raw -Encoding utf8 meu-lote.json | docker compose exec -T api python -m app.adapters.inbound.cli.importar_catalogo
```

A mensagem conta atividades, portanto um lote somente de destinos informa zero
atividades importadas; os destinos são persistidos na mesma transação. Importações
normais são aditivas e não devem ser repetidas indiscriminadamente. `--se-vazio` mantém
a proteção de carga inicial. Uma falha reverte o lote inteiro.

## Como testar

1. Recrie a API com `docker compose up -d --build api` para aplicar a migração.
2. Abra `/docs` e execute `GET /catalogo/destinos` sem Authorize.
3. Confira os filtros, o detalhe pelo ID e a paginação.
4. Em um catálogo já abastecido, Lisboa terá categoria `cidade`; a descrição pode ser
   nula, pois os dados existentes são preservados.
5. Para testar outras categorias, importe um lote revisado como o exemplo acima.

Os testes automatizados cobrem domínio, casos de uso sem banco, memória/PostgreSQL,
consulta anônima, validação, paginação, ausência de escrita pública, importação sem
atividades e migração de um registro existente com retorno à versão anterior.
