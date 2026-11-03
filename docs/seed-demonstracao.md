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

Veja [os lugares e roteiros](seed-destinos-reais.md), [atividades do roteiro](atividades-roteiro.md)
e [avaliações](avaliacoes-atividades.md).
