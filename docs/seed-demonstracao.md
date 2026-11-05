# Dados iniciais de desenvolvimento

O banco novo recebe apenas Orlando, Miami, Rio de Janeiro e Roma, com lugares
reais, usuários com nomes naturais e roteiros sem prefixos. Custos, hospedagens,
viagens e avaliações são dados fictícios de teste.

## Inicialização

```powershell
docker compose up -d --build
```

Em `APP_ENV=development`, o Compose aplica as migrações e executa o seed completo
antes de iniciar a API. Não carrega mais os destinos genéricos antigos, o catálogo
de Lisboa de exemplo ou a conta inicial antiga. Em outros ambientes não executa
esta carga. Fora do Docker:

```powershell
alembic upgrade head
python -m app.adapters.inbound.cli.seed_demo --completo
```

Para executar manualmente no container:

```powershell
docker compose exec api python -m app.adapters.inbound.cli.seed_demo --completo
```

`--referencia AAAA-MM-DD` permite escolher a data base da primeira execução.
O seed usa o registro `dados-iniciais-v2`, e repetir não duplica nem sobrescreve
edições, senhas ou exclusões. A migração cria apenas o schema; quem insere os
dados é o comando. Os commits de cada caso de uso ficam dentro da mesma transação
da carga; qualquer falha desfaz toda a execução.

## Contas

Senha inicial: **`DemoViaja123!`**. Emails e senha foram mantidos para facilitar
os testes e o exemplo de login no Swagger. O banco armazena hashes bcrypt.

| Nome | Email | Cenário |
|---|---|---|
| Ana Souza | `criador.demo@example.com` | Dona dos roteiros da Flórida, Rio, Roma e de 21 planejamentos vazios. |
| Bruno Lima | `editor.demo@example.com` | Editor na Flórida e dono de uma viagem vazia a Roma. |
| Carla Santos | `visualizador.demo@example.com` | Leitura da Flórida e publicação de avaliações de suas ocorrências concluídas. |
| Diego Alves | `externo.demo@example.com` | Dono do roteiro privado de Roma; sem acesso à Flórida. |
| Elisa Costa | `vazio.demo@example.com` | Nenhuma viagem, para testar primeira criação e lista vazia. |
| Felipe Rocha | `descartavel.demo@example.com` | Dono de uma viagem ao Rio com roteiro, para testar exclusões e troca de senha. |

O comando antigo sem `--completo` continua disponível manualmente para criar
`usuario@viajajunto.com`; ele não faz parte da inicialização automática.

## Conteúdo

- Seis contas, quatro destinos e 24 atividades públicas.
- 27 viagens: cinco roteiros preenchidos, uma viagem vazia do editor e 21 planejamentos
  vazios do criador para testar paginação. Os nomes fazem referência aos quatro destinos.
- Seis paradas, 36 ocorrências de atividades e 20 avaliações fictícias.
- Orçamentos definidos nos cinco roteiros preenchidos, incluindo um exemplo excedido.

A listagem padrão do criador tem 20 viagens na primeira página e quatro na segunda.
Editor vê duas viagens; visualizador, externo e conta descartável veem uma cada.
A conta vazia não vê nenhuma. O catálogo de atividades tem 20 itens na primeira
página e quatro na segunda. Todos os dados adicionais criados por você somam-se a esses totais.

O manifesto JSON contém os IDs reais, em `usuarios`, `viagens`, `destinos_catalogo`,
`atividades_catalogo`, `paradas`, `atividades_roteiro` e `avaliacoes`, diretamente na raiz.
Exemplos: `viagens.florida`, `paradas.florida-orlando`, `atividades_catalogo.orlando-1`
e `atividades_roteiro.florida-orlando-1`. Não use números fixos presumidos.

## Lugares e roteiros

| Roteiro | Dono e acesso | Destinos | Orçamento de exemplo |
|---|---|---|---|
| `Orlando e Miami em grupo` | Criador, editor e visualizador | Orlando e Miami | BRL 6.000 |
| `Cultura e paisagens no Rio de Janeiro` | Criador | Rio de Janeiro | BRL 1.200 |
| `História e gastronomia em Roma` | Criador | Roma | BRL 2.000 |
| `Roma: roteiro privado` | Externo | Roma | BRL 500 |

| `Rio para descansar` | Conta descartável | Rio de Janeiro | BRL 1.000 |

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
abertura ou disponibilidade. Cada destino e atividade tem `foto_url` em
`app/application/dados_seed_destinos_reais.py`: uma URL HTTP(S) externa, sem
armazenar o arquivo. Bancos já carregados só recebem novas fotos após o
[reset explícito](reset-banco.md).
Os reviews são fictícios e criados pelas mesmas regras da API, somente
para ocorrências concluídas e participantes das viagens. Há exemplos com mais de
um autor e médias diferentes para testar a busca por nota mínima.


## Testar os casos de uso

Abra <http://localhost:8000/docs>, faça login e use **Authorize** com o token recebido.

| Fluxo | Teste |
|---|---|
| Cadastro | Use um email novo; repita-o para testar duplicidade. |
| Perfil e senha | Consulte `/usuarios/me`; use a conta descartável para editar, trocar senha e excluir. |
| Recuperação de senha | Solicite pela API; leia o token no Mailpit em <http://localhost:8025>; redefina e teste a invalidação da sessão antiga. |
| Logout | Encerre a sessão e confira que aquele JWT passa a receber 401. |
| Resumo/cache | Consulte `/usuarios/resumo`; observe o total e o header `X-Cache`. |
| Viagens | Teste criar, consultar e editar; use a conta vazia e a descartável para ações destrutivas. |
| Paginação | Liste as viagens do criador com páginas 1 e 2; faça o mesmo no catálogo de atividades. |
| Permissões | Flórida: criador/editor editam, visualizador lê, externo recebe 404. Roma privada pertence ao externo. |
| Destinos | Consulte as cidades por nome ou país; liste as paradas da Flórida, altere estadias e reordene com todos os IDs. |
| Atividades | Liste a agenda, crie/edite/remova ocorrências e teste custos, datas e duração inválidos. |
| Avaliações | Magic Kingdom Park, Vizcaya, Cristo Redentor e Coliseu já têm reviews. Reenvie uma nota para atualizar sua avaliação sem duplicar. |
| Nota mínima | Combine `nota_minima`, categoria, localização e destino no catálogo público. |
| Orçamento | Compare os saldos da Flórida e de Roma privada, que excede seu limite. |
| Isolamento | Misture IDs de atividades/paradas de viagens diferentes; espere 404. |
| Cascatas | Exclua a conta descartável; seu roteiro é removido, mas o catálogo e os reviews ficam preservados, com autor nulo. |

## Bancos com a versão antiga

A carga antiga foi substituída. Para ficar apenas com os novos exemplos, o banco
local antigo precisa ser limpo explicitamente antes de semear. O seed **não apaga
dados automaticamente**, e recusa apropriar contas com emails já existentes.
Não remova só o registro do seed: as contas e os dados antigos continuariam no banco.
Use o [comando de reset explícito](reset-banco.md): ele verifica o destino,
limpa o banco e reaplica migrações e seed. Depois, inicie a API normalmente.
Reiniciar uma base já preenchida com esta versão preserva as alterações dos testes.

Veja também [atividades do roteiro](atividades-roteiro.md) e [avaliações](avaliacoes-atividades.md).

## Referências da curadoria

Consultadas em 03/11/2026, para nomes e descrições gerais, sem coletar imagens:

- [Visit Orlando: Disney Springs e East End Market](https://www.visitorlando.com/things-to-do/theme-parks/walt-disney-world-resort/disney-springs/).
- [Visit Orlando: atrações da região](https://www.visitorlando.com/blog/post/holiday-season-orlando/).
- [Greater Miami: Bayfront Park e Bayside](https://www.miamiandbeaches.com/l/outdoor-experiences/bayfront-park/2443).
- [Miami-Dade: Metromover](https://www.miamidade.gov/global/transportation/metromover.page).
- [Prefeitura do Rio: pontos turísticos](https://controladoria.prefeitura.rio/pontos-turisticos/).
- [Turismo Roma: roteiro pelo Coliseu, Trevi e Villa Borghese](https://turismoroma.it/it/itinerari/roma-72-ore).
