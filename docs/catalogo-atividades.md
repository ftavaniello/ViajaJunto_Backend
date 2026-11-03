# Catálogo interno de atividades — issue #20

O catálogo contém dados reutilizáveis de locais e experiências. Uma atividade pertence
obrigatoriamente a um destino do catálogo. Não contém datas, duração, custos, status
ou participantes de viagens: esses dados pertencem ao roteiro privado.

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
| `nota_minima` | Média mínima inclusiva entre 1 e 5; exclui atividades sem avaliações |
| `pagina` | Inteiro a partir de 1; padrão 1 |
| `tamanho_pagina` | De 1 a 100; padrão 20 |

Textos são aparados; espaços em branco equivalem a filtro ausente. As buscas não
distinguem maiúsculas de minúsculas, mas não removem acentos. `%` e `_` são
caracteres literais, não curingas. Campos desconhecidos são rejeitados com 422.

Exemplo: `/catalogo/atividades?nome=passeio&categoria=cultura&localizacao=lisboa`.

A resposta contém `itens`, `pagina`, `tamanho_pagina` e `tem_proxima`.
Ordenação crescente por ID, com limite e deslocamento aplicados no PostgreSQL.
Sem resultados ou após a última página, `itens=[]` e `tem_proxima=false`.
Inserções ou exclusões entre consultas podem alterar a composição das páginas.

O destino associado inclui também categoria e descrição gerais (issue #18).
Veja [catálogo de destinos](catalogo-destinos.md) para pesquisa e seleção.

Cada item tem ID, nome, descrição, categoria, endereço, latitude/longitude,
`foto_url`, `google_place_id`, `fonte` e o destino (ID, cidade, país e dados geográficos).
O modelo aprovado na migração usa uma foto por registro, representada por URL;
não há armazenamento ou upload de imagens. URLs são referências e não são baixadas
pelo backend. Não são retornados usuários, membros, convites nem dados do roteiro.
O vocabulário de categorias segue `CategoriaAtividade` e os CHECKs existentes no banco,
que divergem dos tipos exemplificados no documento inicial de arquitetura.

## Avaliações — RF22–24

O catálogo retorna média e total calculados de todas as avaliações, inclusive de
contas excluídas. Sem reviews: média nula, total zero e lista vazia. A listagem
contém resumos; o detalhe inclui até 20 reviews mais recentes. Todos os reviews
podem ser consultados em `GET /catalogo/atividades/{atividade_id}/avaliacoes`.

Cada review contém ID, nota de 1 a 5, comentário opcional, nome público do autor
(nulo se a conta foi excluída) e data de criação. Não expõe email nem dados de viagem.
O filtro `nota_minima` é aplicado à média sem arredondamento, antes de paginar.
Veja [publicação, permissões e exemplos](avaliacoes-atividades.md).

## Seed automático no desenvolvimento

O Compose aplica as migrações e carrega [os dados iniciais](seed-demonstracao.md)
com Orlando, Miami, Rio de Janeiro e Roma. O catálogo antigo de Lisboa não é mais
carregado automaticamente. O arquivo `docs/catalogo-exemplo.json` continua disponível
para testar manualmente o importador. Fora do Compose, execute o seed ou o importador
explicitamente. A imagem de produção não cria dados de teste automaticamente.

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
O importador não aceita caminhos de arquivos em argumentos. Para lotes personalizados,
recebe JSON pela entrada padrão; `--exemplo` seleciona exclusivamente o arquivo fixo
do projeto, sem permitir escolher outro caminho. No PowerShell local, por exemplo:

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new()
Get-Content -Raw -Encoding utf8 meu-lote.json | python -m app.adapters.inbound.cli.importar_catalogo
```

O lote pode conter apenas destinos, omitindo `atividades`; a mensagem final conta
atividades, portanto informa zero nesses lotes, mesmo com destinos cadastrados.
As chaves de `destinos`, como `lisboa`, são referências locais ao arquivo, não IDs
persistidos. Cada atividade referencia uma dessas chaves em `destino`.

No ambiente Python com dependências instaladas e `DATABASE_URL` configurada:

```sh
alembic upgrade head
python -m app.adapters.inbound.cli.importar_catalogo --exemplo
```

Com a API do Docker Compose, após reconstruir a imagem para incluir o comando:

```sh
docker compose up -d --build api
docker compose exec -T api python -m app.adapters.inbound.cli.importar_catalogo < docs/catalogo-exemplo.json
```

A segunda linha usa redirecionamento de shell POSIX/cmd. No PowerShell, use:

```powershell
Get-Content -Raw -Encoding utf8 docs/catalogo-exemplo.json | docker compose exec -T api python -m app.adapters.inbound.cli.importar_catalogo
```

A importação valida o arquivo inteiro antes de gravar e confirma o lote numa única
transação. Nome vazio, categoria inválida, coordenada fora de faixa, referência a
destino ausente ou URL de foto fora de HTTP/HTTPS são rejeitados. Uma falha no banco
reverte destinos e atividades do lote inteiro. IDs externos não nulos são únicos.

**Importação sem `--se-vazio` é aditiva:** não é atualização nem sincronização idempotente. Reimportar
um arquivo com IDs externos repetidos cancela o lote; sem IDs externos, reimportar
cria novos registros. Execute cada lote uma vez e confira o resultado. A evolução
do mecanismo de atualização deve preservar as referências do roteiro e avaliações.

## Teste no Swagger

1. Inicie a API pelo Docker Compose; em catálogo vazio, o seed abastece os exemplos automaticamente.
2. Abra `/docs`; as operações da tag **Catálogo** não precisam de Authorize.
3. Liste as atividades e experimente os filtros e `tamanho_pagina=1`.
4. Use um ID retornado para consultar o detalhe.
5. Confira as informações da foto/localização e média, total e reviews públicos.

Os testes automatizados usam PostgreSQL exclusivo (`viajajunto_test`) e validam
persistência, filtros, paginação, consulta anônima, contrato público e rollback.
