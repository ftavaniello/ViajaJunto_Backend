# Catálogo interno de atividades — issue #20

O catálogo contém dados reutilizáveis de locais e experiências. Uma atividade pertence
obrigatoriamente a um destino do catálogo. Não contém datas, duração, custos, status
ou participantes de viagens: esses dados de planejamento pertencem à issue #21.

## Consulta pública

Não exige token, inclusive para visitantes:

- `GET /catalogo/atividades`: busca paginada.
- `GET /catalogo/atividades/{atividade_id}`: detalhe; 404 se não existir, 422 para ID inválido.

Filtros opcionais, combinados por **E**:

| Parâmetro | Significado |
|---|---|
| `nome` | Trecho do nome da atividade |
| `categoria` | `alimentacao`, `transporte`, `cultura`, `lazer`, `compras`, `outros` |
| `localizacao` | Trecho da cidade, do código de país ou do endereço |
| `destino_catalogo_id` | Destino exato pelo ID público |
| `pagina` | Inteiro a partir de 1; padrão 1 |
| `tamanho_pagina` | De 1 a 100; padrão 20 |

Textos são aparados; espaços em branco equivalem a filtro ausente. As buscas não
distinguem maiúsculas de minúsculas, mas não removem acentos. `%` e `_` são
caracteres literais, não curingas. Campos desconhecidos, incluindo `nota_minima`,
são rejeitados com 422, pois o filtro por nota pertence à #23.

Exemplo: `/catalogo/atividades?nome=passeio&categoria=cultura&localizacao=lisboa`.

A resposta contém `itens`, `pagina`, `tamanho_pagina` e `tem_proxima`.
Ordenação crescente por ID, com limite e deslocamento aplicados no PostgreSQL.
Sem resultados ou após a última página, `itens=[]` e `tem_proxima=false`.
Inserções ou exclusões entre consultas podem alterar a composição das páginas.

Cada item tem ID, nome, descrição, categoria, endereço, latitude/longitude,
`foto_url`, `google_place_id`, `fonte` e o destino (ID, cidade, país e dados geográficos).
O modelo aprovado na migração usa uma foto por registro, representada por URL;
não há armazenamento ou upload de imagens. URLs são referências e não são baixadas
pelo backend. Não são retornados usuários, membros, convites nem dados do roteiro.
O vocabulário de categorias segue `CategoriaAtividade` e os CHECKs existentes no banco,
que divergem dos tipos exemplificados no documento inicial de arquitetura.

## Avaliações: contrato preparado para a #23

Nesta entrega, `avaliacoes_disponiveis=false`, `media_avaliacoes=null`,
`total_avaliacoes=null` e `reviews=[]`. Isso significa **integração ainda indisponível**,
não uma contagem calculada de zero. Não são consultadas nem expostas avaliações já
inseridas diretamente no banco. O frontend deve ocultar estrelas/médias nesse estado.
O contrato de review está reservado no OpenAPI: ID, nota de 1 a 5, comentário,
nome público do autor e data de criação.

Quando a integração da #23 existir, uma atividade ainda sem avaliações deverá ter
média nula, total zero e reviews vazios. Não usar nota zero, pois as notas válidas
vão de 1 a 5. Média real, reviews e filtro por nota continuam pendentes na #23;
RF23 e RF24 não estão integralmente concluídos nesta issue.

## Origem e abastecimento autorizado

Nesta versão a origem é **curadoria manual pela equipe operadora**, persistida como
`fonte=manual`. A migração `f3b8c1d29a40` adiciona essa coluna e atribui o mesmo valor
a registros anteriores. A referência externa opcional é `google_place_id`; ela não
significa sincronização nem validação automática no Google Places. A integração
externa prevista na arquitetura permanece futura; não há credencial externa exigida.

Somente operadores com acesso ao servidor/ambiente da aplicação e às credenciais do
banco podem executar a importação. A autorização é do ambiente operacional; o JWT
de um usuário comum não concede acesso ao comando. Não há endpoint público ou
endpoint de usuário para cadastrar, editar ou remover registros do catálogo.

Revise a origem, as descrições e as permissões de uso das fotos antes de importar
um arquivo. Use dados que a equipe esteja autorizada a disponibilizar publicamente.
O arquivo `docs/catalogo-exemplo.json` contém dados fictícios para desenvolvimento.
As chaves de `destinos`, como `lisboa`, são referências locais ao arquivo, não IDs
persistidos. Cada atividade referencia uma dessas chaves em `destino`.

No ambiente Python com dependências instaladas e `DATABASE_URL` configurada:

```sh
alembic upgrade head
python -m app.adapters.inbound.cli.importar_catalogo docs/catalogo-exemplo.json
```

Com a API do Docker Compose, após reconstruir a imagem para incluir o comando:

```sh
docker compose up -d --build api
docker compose exec -T api python -m app.adapters.inbound.cli.importar_catalogo /dev/stdin < docs/catalogo-exemplo.json
```

A segunda linha usa redirecionamento de shell POSIX/cmd. No PowerShell, use:

```powershell
Get-Content -Raw -Encoding utf8 docs/catalogo-exemplo.json | docker compose exec -T api python -m app.adapters.inbound.cli.importar_catalogo /dev/stdin
```

A importação valida o arquivo inteiro antes de gravar e confirma o lote numa única
transação. Nome vazio, categoria inválida, coordenada fora de faixa, referência a
destino ausente ou URL de foto fora de HTTP/HTTPS são rejeitados. Uma falha no banco
reverte destinos e atividades do lote inteiro. IDs externos não nulos são únicos.

**Importação aditiva:** não é atualização nem sincronização idempotente. Reimportar
um arquivo com IDs externos repetidos cancela o lote; sem IDs externos, reimportar
cria novos registros. Execute cada lote uma vez e confira o resultado. A evolução
do mecanismo de atualização deve preservar as referências do roteiro e avaliações.

## Teste no Swagger

1. Abasteça o banco de desenvolvimento usando o comando de importação.
2. Abra `/docs`; as operações da tag **Catálogo** não precisam de Authorize.
3. Liste as atividades e experimente os filtros e `tamanho_pagina=1`.
4. Use um ID retornado para consultar o detalhe.
5. Confira as informações da foto/localização e os campos reservados de avaliações.

Os testes automatizados usam PostgreSQL exclusivo (`viajajunto_test`) e validam
persistência, filtros, paginação, consulta anônima, contrato público e rollback.
