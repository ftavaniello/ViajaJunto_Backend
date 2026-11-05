# Integração de locais por porta de aplicação (Geoapify) — issue #23

O catálogo interno de atividades pode ser abastecido com locais reais de um
fornecedor externo. O backend consulta o fornecedor por uma **porta**
(`ProvedorLocais`) e transforma a resposta em registros do catálogo. Avaliações e
roteiros continuam apontando para o catálogo interno, nunca para o fornecedor.

## Por que Geoapify e não Google Places

A arquitetura previa o Google Places, mas a equipe não tem acesso à API oficial.
O fornecedor escolhido foi a
[Places API do Geoapify](https://apidocs.geoapify.com/docs/places/):

- tem plano gratuito sem cartão (3.000 créditos por dia; cada 20 locais custam 1 crédito);
- busca por categoria em volta de uma coordenada, que é o que o catálogo precisa;
- usa dados do OpenStreetMap e devolve um `place_id` para identificar cada local;
- exige chave, o que permite exercitar credenciais fora do código.

Como o domínio só conhece a porta, trocar de fornecedor é escrever outro adaptador
e acrescentar um valor em `FonteCatalogo`. Nenhum caso de uso muda.

## Arquitetura

| Camada | Arquivo | Papel |
|---|---|---|
| Porta | `app/domain/ports/provedor_locais.py` | `ProvedorLocais.buscar_proximos(...)` devolve `LocalExterno` |
| Caso de uso | `app/application/use_cases/enriquecer_catalogo.py` | Regras: deduplicação, preservação, transação |
| Adaptador | `app/adapters/outbound/locais/geoapify_provedor_locais.py` | HTTP, chave, JSON e códigos HTTP do Geoapify |
| Fake | `app/adapters/outbound/locais/provedor_locais_memory.py` | Fornecedor falso usado nos testes |
| Configuração | `app/infrastructure/locais.py` | Lê a chave e monta o adaptador |
| Entrada | `app/adapters/inbound/cli/enriquecer_catalogo.py` | Comando de operador |

O adaptador usa só a biblioteca padrão (`urllib`), sem SDK nem dependência nova.

## Quem executa

Assim como o importador JSON, o enriquecimento é uma **operação de operador**:
roda no servidor, com acesso ao banco, pela linha de comando. Não há endpoint de
usuário para disparar buscas no fornecedor, o que protege a cota e a chave.

```bash
python -m app.adapters.inbound.cli.enriquecer_catalogo --destino 1 --categoria passeio
python -m app.adapters.inbound.cli.enriquecer_catalogo --destino 1 --categoria refeicao \
    --raio 3000 --limite 50
```

| Opção | Padrão | Faixa |
|---|---|---|
| `--destino` | obrigatório | ID de `destinos_catalogo`, que precisa ter latitude e longitude |
| `--categoria` | obrigatório | `passeio`, `refeicao`, `hospedagem`, `transporte`, `outro` |
| `--raio` | 5000 | 100 a 50.000 metros a partir do destino |
| `--limite` | 20 | 1 a 100 locais |

Saída de sucesso: `Catálogo enriquecido: 12 criada(s), 3 atualizada(s), 0 ignorada(s).`

### Mapeamento de categorias

| ViajaJunto | Categorias Geoapify |
| --- | --- |
| `passeio` | Museus, cultura, atrações, parques, praias, zoológicos e parques temáticos |
| `refeicao` | Restaurantes e cafés |
| `hospedagem` | `accommodation` (inclui hotéis, hostels e outras acomodações) |
| `transporte` | `public_transport` |
| `outro` | Centros comerciais e `tourism` |

Os tipos correspondem ao documento original de arquitetura. Referência do fornecedor:
[Geoapify Places API — categorias](https://apidocs.geoapify.com/docs/places/).

## Regras

- **Sem duplicação:** cada local é identificado por `(fonte, id_externo)`, único no
  banco (`uq_catalogo_atividades_fonte_id_externo`). Reexecutar o comando atualiza
  o registro existente em vez de criar outro. O mesmo local repetido na resposta
  conta uma vez.
- **Preservação:** a atualização mexe só em nome, endereço e coordenadas. O `id`, o
  destino, a categoria, a descrição e a foto ficam como estão. Por isso avaliações,
  médias, atividades de roteiro e a curadoria da equipe continuam válidas.
  Um local que aparece buscando a partir de outro destino continua no destino original.
- **Nada é apagado:** um local que deixa de vir do fornecedor permanece no catálogo.
- **Registros manuais não são tocados:** `fonte=manual` com o mesmo `id_externo` é
  outro registro.
- **Itens incompletos** (sem `place_id`, nome ou coordenadas) são descartados pelo
  adaptador; itens que a entidade recusa contam como `ignorada(s)` sem cancelar o lote.
- **Transação:** a consulta ao fornecedor acontece antes de abrir a transação. Se
  o fornecedor falhar, nada é gravado. Se o banco falhar, o lote inteiro é desfeito.

## Falhas do fornecedor

| Situação | Erro de domínio | Mensagem da CLI (código de saída 2) |
|---|---|---|
| Sem chave configurada ou arquivo ilegível | `CredencialProvedorLocaisInvalida` | `Configure GEOAPIFY_API_KEY ...` |
| HTTP 401 ou 403 | `CredencialProvedorLocaisInvalida` | `Geoapify recusou a chave configurada (HTTP 401)` |
| HTTP 429 | `LimiteProvedorLocaisExcedido` | `Limite de requisições ... Tente novamente em N s.` (com `Retry-After`) |
| Timeout | `ProvedorLocaisIndisponivel` | `Geoapify não respondeu em 10 s` |
| HTTP 5xx | `ProvedorLocaisIndisponivel` | `Geoapify indisponível (HTTP 503)` |
| Outro HTTP 4xx | `ProvedorLocaisIndisponivel` | `Geoapify recusou a consulta (HTTP 400)` |
| Sem rede ou DNS | `ProvedorLocaisIndisponivel` | `Não foi possível conectar ao Geoapify` |
| JSON ilegível | `ProvedorLocaisIndisponivel` | `Geoapify devolveu uma resposta inválida` |

Destino inexistente, destino sem coordenadas e parâmetros fora da faixa saem com
código 1, antes de qualquer chamada ao fornecedor.

A chave vai na query string, como o Geoapify exige. Ela **nunca** aparece nas
mensagens de erro nem nas exceções encadeadas (`raise ... from None`), e há teste
garantindo isso.

## Configuração

| Variável | Padrão | Uso |
|---|---|---|
| `GEOAPIFY_API_KEY` | vazio | Chave da Places API |
| `GEOAPIFY_API_KEY_FILE` | vazio | Caminho de arquivo com a chave (segredo montado); usado se a variável acima estiver vazia |
| `LOCAIS_TIMEOUT_SECONDS` | 10 | Timeout de cada requisição; precisa ser maior que zero |

A API sobe normalmente sem chave: só o comando de enriquecimento a exige. Nunca
commite a chave; use o `.env` local (fora do git) ou um segredo do ambiente.

## Mudança no contrato da API

Nas respostas de `/catalogo/atividades` e `/catalogo/destinos` (inclusive o
destino aninhado e o ranking), o campo `google_place_id` foi substituído por:

- `id_externo`: identificador do local no fornecedor (nulo para curadoria sem referência);
- `fonte`: `manual` ou `geoapify`. Antes só existia nas atividades; agora também nos destinos.

O importador JSON aceita `id_externo` no lugar de `google_place_id`. A migração
`a7d3e8c25f61` renomeia a coluna, mantém os valores existentes como `fonte=manual`
e troca a unicidade global por `UNIQUE (fonte, id_externo)`. O downgrade preserva
os registros vindos do fornecedor (avaliações apontam para eles), mas os converte
em manuais sem `id_externo`.

## Verificação real da integração

Os testes automáticos usam um fornecedor falso e não acessam a rede. Para validar
a integração de verdade:

1. Crie uma conta gratuita em <https://myprojects.geoapify.com>, crie um projeto e
   copie a chave da API.
2. No `.env` local, preencha `GEOAPIFY_API_KEY=<sua chave>`.
3. Suba o banco e aplique as migrações (`alembic upgrade head`). Com o seed de
   desenvolvimento carregado, descubra o ID de Orlando:

   ```bash
   curl -s "http://localhost:8000/catalogo/destinos?nome=orlando" | python -m json.tool
   ```

4. Rode o comando para esse destino:

   ```bash
   python -m app.adapters.inbound.cli.enriquecer_catalogo --destino <id> --categoria passeio --limite 10
   ```

   Esperado: `Catálogo enriquecido: N criada(s), 0 atualizada(s), 0 ignorada(s).`
5. Confira as atividades novas, com `"fonte": "geoapify"` e `id_externo` preenchido:

   ```bash
   curl -s "http://localhost:8000/catalogo/atividades?destino_catalogo_id=<id>&tamanho_pagina=50" \
     | python -m json.tool
   ```

6. Rode o mesmo comando de novo. Esperado: `0 criada(s), N atualizada(s)`, sem
   registros duplicados.
7. Teste uma falha: troque a chave por um valor inválido e rode de novo. Esperado:
   `Nada foi gravado: Geoapify recusou a chave configurada (HTTP 401).` e código de
   saída 2.

Também é possível conferir a chave direto no fornecedor, sem passar pelo backend:

```bash
curl -s "https://api.geoapify.com/v2/places?categories=entertainment.museum&filter=circle:-81.379234,28.538336,5000&limit=3&apiKey=$GEOAPIFY_API_KEY"
```

## Fora do escopo

Reservas, pagamentos e compra de passagens; endpoint público de busca no
fornecedor; sincronização automática agendada; fotos (a Places API não as fornece).
