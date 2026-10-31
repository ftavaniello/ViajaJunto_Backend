# Seed completo de demonstração

Carga de desenvolvimento para testes manuais dos casos de uso já implementados. Não depende
de o banco estar vazio: adiciona exemplos identificados por `[Demo]`, sem alterar
viagens, contas ou catálogos existentes. Não substitui a suíte automatizada.

## Executar

No Docker Compose, basta subir o projeto:

```powershell
docker compose up -d --build
```

Com `APP_ENV=development` (padrão local), a inicialização aplica as migrações,
prepara a conta inicial e o catálogo de exemplo e executa o seed completo antes
de iniciar a API. Assim, um banco novo recebe todos os cenários automaticamente.
Nos próximos starts, o registro da carga impede duplicações e preserva edições e
exclusões. Um banco existente que ainda não recebeu a carga também será preenchido.

Para executar manualmente com a API e o PostgreSQL locais em execução:

```powershell
docker compose exec api alembic upgrade head
docker compose exec api python -m app.adapters.inbound.cli.seed_demo --completo
```

Sem Docker, com o ambiente virtual e a configuração local carregados:

```powershell
alembic upgrade head
python -m app.adapters.inbound.cli.seed_demo --completo
```

O comando exige `APP_ENV=development` (inclusive `test` é recusado para esta carga).
O comando manual não exige reiniciar a API. Fora do Compose, a carga continua
sendo feita pelo comando acima. `SEED_CATALOGO=false` controla apenas o antigo
catálogo de exemplo; não desativa os cenários do seed completo em desenvolvimento.
A migração cria apenas a tabela técnica `seeds_demonstracao`, sem semear dados.

A data base é o dia da primeira execução. Para uma apresentação reproduzível:

```powershell
docker compose exec api python -m app.adapters.inbound.cli.seed_demo --completo --referencia 2026-10-31
```

A viagem passada começa 30 dias antes e a compartilhada 30 dias depois da referência.
Os períodos ficam fixos após a primeira carga; executar novamente não avança datas.
Os exemplos incluem conclusões lançadas manualmente em viagens futuras, permitidas
pelo contrato atual; isso não representa comprovação de presença no local.

## Contas

Senha inicial de todas as contas abaixo: **`DemoViaja123!`**. Credenciais públicas
exclusivamente de demonstração local; o banco armazena apenas hashes bcrypt.

| Email | Cenário |
|---|---|
| `criador.demo@example.com` | Dono da viagem compartilhada, da passada e de 21 viagens para paginação (23 próprias). |
| `editor.demo@example.com` | Editor na compartilhada e dono de outra viagem. |
| `visualizador.demo@example.com` | Apenas leitura na compartilhada. |
| `externo.demo@example.com` | Dono de uma viagem privada; sem acesso à compartilhada. |
| `vazio.demo@example.com` | Nenhuma viagem, para testar lista vazia e primeira criação. |
| `descartavel.demo@example.com` | Uma viagem própria com roteiro, para editar/excluir conta, viagem e filhos. |

A conta antiga `usuario@viajajunto.com` é independente: entre com as contas acima
para ver os novos cenários. Recuperação de senha usa o Mailpit local, em
<http://localhost:8025>, sem enviar mensagens aos endereços de exemplo.

## Conteúdo e IDs

- 26 viagens: compartilhada, passada, privada, própria do editor, descartável e 21 vazias.
- 24 destinos públicos de demonstração: PT e BR, cobrindo as quatro categorias.
- 144 atividades públicas: seis categorias em cada destino; paginação inclusive por categoria.
- 15 paradas: três em cada uma das cinco viagens principais, com ordem e períodos válidos.
- 30 atividades privadas: primeiras duas paradas de cada roteiro com status pendente,
  confirmada e concluída; terceira parada vazia. Custos `0.00`, `45.50` e `120.00`,
  horários às 09h, 14h e sem horário; durações presentes/ausentes e autor/data de conclusão.

Locais, hospedagens e atividades são exemplos fictícios, sem integração com Google Places.
Dados públicos são separados das anotações e custos privados de cada roteiro.

O comando imprime um **manifesto JSON** com os IDs reais gerados pelo banco,
agrupados por nomes estáveis, como:

```text
usuarios.criador
viagens.compartilhada
viagens.privada
viagens.descartavel
paradas.compartilhada-parada-1
atividades_roteiro.compartilhada-parada-1-pendente
destinos_catalogo.destino-01
atividades_catalogo.destino-01-cultura
```

São chaves no JSON, não IDs fixos. Use os valores numéricos no Swagger. Repetir
o comando imprime o mesmo manifesto e informa que os dados foram mantidos.

## Roteiro de testes no Swagger

Abra <http://localhost:8000/docs>, execute `POST /auth/login` com email/senha e
copie `access_token` para **Authorize**. Troque o token ao mudar de conta.

| Caso de uso | Como testar com estes dados |
|---|---|
| Cadastrar usuário | `POST /usuarios` com email novo; repetir o email valida duplicidade. |
| Login e consulta de perfil | Entre com qualquer conta e use `GET /usuarios/me`; senha incorreta deve receber 401. |
| Atualizar perfil/senha | Use a conta descartável em `PATCH /usuarios/me` e `/usuarios/me/senha`; após trocar senha, faça novo login. |
| Recuperar/redefinir senha | Solicite em `POST /auth/recuperar-senha`, abra o email no Mailpit e use o token em `/auth/redefinir-senha`; confira invalidação das sessões. |
| Logout | `POST /auth/logout`; usar novamente aquele JWT deve receber 401. |
| Resumo e cache | `GET /usuarios/resumo` autenticado; total inclui contas já existentes; observe `X-Cache`. |
| Criar viagem | Entre como `vazio`, use `POST /viagens`, consulte e altere a viagem criada. |
| Listar viagens | Como criador, página 1 padrão tem 20 e `tem_proxima=true`; página 2 tem três exemplos, sem dados extras próprios. Editor vê a própria e a compartilhada; visualizador vê uma; vazio vê zero antes de criar. |
| Consultar/alterar/excluir viagem | Use os IDs do manifesto. Criador pode excluir; editor pode editar a compartilhada; visualizador não pode editar. Use a viagem descartável para exclusão. |
| Catálogo de destinos | Sem login, liste, filtre `nome=Demo`, `pais_codigo=PT`, categoria, varie paginação e consulte um ID. |
| Catálogo de atividades | Sem login, filtre `nome=Demo`, categoria, localização e `destino_catalogo_id`; consulte detalhes. |
| Importação operacional de catálogo | Siga [o comando de importação](catalogo-atividades.md) com outro lote, por stdin; não há escrita pública no Swagger. |
| Destinos do roteiro | Na compartilhada, liste/consulte, crie uma parada com destino do catálogo dentro do período, altere hospedagem/descrição e use `PUT /viagens/{id}/destinos/ordem` com todos os IDs. |
| Atividades do roteiro | Liste a primeira parada: confirmada 09h, pendente 14h, concluída sem hora. Crie na terceira parada usando uma atividade do mesmo destino público. Altere data, custo, horário, duração e status; reabrir conclusão limpa os comprovantes. |
| Exclusões em cascata | Use roteiro descartável: remova uma atividade, uma parada ou a viagem. Catálogo público deve continuar disponível. Exclua a conta descartável por último. |
| Permissões | Repita as leituras e escritas na compartilhada como editor, visualizador e externo. Visualizador recebe 403 nas escritas; externo recebe 404 nas leituras e escritas, preservando privacidade. |
| Isolamento dos IDs | Misture ID de parada/atividade de outra viagem ou parada em uma URL; espere 404. |
| Regras de período/custo | Tente datas fora da viagem/parada, custo negativo, duração zero, categoria/status inválidos: devem ser recusados. |

Para editar a compartilhada após mudar as contas, refaça login e atualize o token.
Veja também [destinos](destinos-roteiro.md) e [atividades do roteiro](atividades-roteiro.md)
para exemplos exatos de payload. As permissões são preparadas pelo seed porque a
API de gestão de membros ainda não foi implementada. Orçamento completo, avaliações,
ranking e outros recursos ainda não implementados não são simulados por esta carga.

## Reexecução e preservação

A carga inteira e seu registro são confirmados juntos. Falhas desfazem tudo que
esta execução adicionou. Um lock transacional serializa execuções concorrentes.
Se uma conta reservada já existir antes da primeira carga, o comando recusa a operação
inteira, sem apropriar a conta, trocar senha ou conceder permissões a ela.

Após sucesso, executar de novo **não duplica, não sobrescreve edições e não recria
registros excluídos**, mesmo informando outra referência. O manifesto representa a
carga original; IDs excluídos durante testes podem deixar de existir. Não há reset
ou limpeza automática. Para repetir testes destrutivos, crie outra conta/viagem via
API ou use um banco local separado. Não remova apenas o registro de execução para
forçar nova carga: os emails reservados serão detectados como colisão.

A contagem de usuários é invalidada após o commit da carga. Não são semeados JWTs,
sessões revogadas ou tokens de recuperação: obtenha-os pelos fluxos reais da API.
